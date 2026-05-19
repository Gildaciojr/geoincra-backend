from __future__ import annotations

import json
import math
import os
import re
from datetime import datetime
from math import cos, radians, sin, sqrt
from typing import Any, Optional

from shapely.geometry import Polygon
from sqlalchemy.orm import Session

from app.crud.documento_tecnico_crud import create_documento_tecnico
from app.crud.sigef_export_crud import exportar_sigef_csv
from app.models.document import Document
from app.models.geometria import Geometria
from app.models.imovel import Imovel
from app.models.matricula import Matricula
from app.schemas.documento_tecnico import DocumentoTecnicoCreate
from app.schemas.ocr_result_structured import OCRStructured
from app.schemas.sigef_export import SigefCsvExportRequest
from app.services.cad_export_service import CadExportService
from app.services.croqui_service import CroquiService
from app.services.geometria_service import GeometriaService
from app.services.matricula_analysis_service import MatriculaAnalysisService
from app.services.memorial_parser_service import MemorialParserService
from app.services.memorial_service import MemorialService
from app.services.ocr_normalizer import normalizar_dados_ocr


class OcrPipelineService:
    FECHAMENTO_TOLERANCIA_METROS = 2.0

    @staticmethod
    def _rollback_safely(db: Session) -> None:
        try:
            db.rollback()
        except Exception:
            pass

    @staticmethod
    def _json_safe(value: Any) -> Any:
        if isinstance(value, dict):
            return {str(k): OcrPipelineService._json_safe(v) for k, v in value.items()}
        if isinstance(value, list):
            return [OcrPipelineService._json_safe(v) for v in value]
        if isinstance(value, tuple):
            return [OcrPipelineService._json_safe(v) for v in value]
        if isinstance(value, datetime):
            return value.isoformat()
        return value

    @staticmethod
    def _build_file_url(base_url: str, path_value: str | None) -> str | None:
        if not path_value:
            return None
        return f"{base_url}/{path_value.replace('app/', '')}"

    @staticmethod
    def executar_pipeline(
        db: Session,
        document_id: int,
        ocr_result_id: int | None,
        prompt_categoria: str,
        dados_extraidos: dict[str, Any],
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "success": False,
            "document_id": document_id,
            "ocr_result_id": ocr_result_id,
            "categoria": prompt_categoria,
            "steps": {},
            "errors": [],
        }

        if not prompt_categoria:
            result["errors"].append("Categoria de prompt ausente.")
            return result

        categoria = OcrPipelineService._normalizar_categoria(prompt_categoria)

        categorias_matricula = [
            "matricula_imovel",
            "analise_matricula_completa",
            "analise_matricula",
            "analise de matricula de imovel",
            "analise tecnica completa de matricula",
            "análise de matrícula de imóvel",
            "análise técnica completa de matrícula",
        ]

        categorias_matricula_normalizadas = [
            OcrPipelineService._normalizar_categoria(item)
            for item in categorias_matricula
        ]

        if categoria in categorias_matricula_normalizadas:
            dados_normalizados: dict[str, Any] = normalizar_dados_ocr(dados_extraidos)

            try:
                OCRStructured(**dados_normalizados)
            except Exception as exc:
                return {
                    "success": False,
                    "document_id": document_id,
                    "ocr_result_id": ocr_result_id,
                    "categoria": prompt_categoria,
                    "steps": {},
                    "errors": [f"OCR inválido estruturalmente: {str(exc)}"],
                }

            return OcrPipelineService._pipeline_matricula(
                db=db,
                document_id=document_id,
                ocr_result_id=ocr_result_id,
                dados=dados_normalizados,
            )

        result["errors"].append(
            f"Pipeline sem tratamento para categoria: {prompt_categoria}"
        )
        return result

    @staticmethod
    def _normalizar_categoria(texto: str) -> str:
        mapa = str.maketrans(
            "áàãâäéèêëíìîïóòõôöúùûüç",
            "aaaaaeeeeiiiiooooouuuuc",
        )
        return texto.lower().strip().translate(mapa)

    @staticmethod
    def _pipeline_matricula(
        db: Session,
        document_id: int,
        ocr_result_id: int | None,
        dados: dict[str, Any],
    ) -> dict[str, Any]:
        print(f"🔎 Iniciando pipeline de matrícula para documento {document_id}")

        # 🔥 CORREÇÃO CRÍTICA — GARANTE QUE NUNCA QUEBRE O PIPELINE
        confrontantes_db: list = []

        result: dict[str, Any] = {
            "success": False,
            "document_id": document_id,
            "ocr_result_id": ocr_result_id,
            "pipeline": "MATRICULA",
            "steps": {
                "matricula": {},
                "matricula_pdf": {},
                "analise_juridica": {},
                "geometria": {},
                "confrontantes": {},
                "sigef_validacao": {},
                "memorial": {},
                "croqui": {},
                "cad": {},
                "txt": {},
                "dxf": {},
                "shp": {},
                "sigef_csv": {},
            },
            "errors": [],
        }

        base_url = "https://geoincra.escriturafacil.com"

        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise Exception("Documento não encontrado")

        imovel: Optional[Imovel] = (
            db.query(Imovel)
            .filter(Imovel.project_id == doc.project_id)
            .first()
        )
        if not imovel:
            raise Exception("Projeto não possui imóvel cadastrado")

        matricula: Optional[Matricula] = None

        # ================= MATRÍCULA =================
        try:
            matricula = OcrPipelineService._upsert_matricula(
                db=db,
                imovel=imovel,
                dados=dados,
            )

            if matricula:
                result["steps"]["matricula"] = {
                    "success": True,
                    "matricula_id": matricula.id,
                    "numero_matricula": matricula.numero_matricula,
                    "comarca": matricula.comarca,
                    "arquivo_path": None,
                    "arquivo_url": None,
                }

                # ================= MATRÍCULA PDF =================
                try:
                    from app.services.matricula_pdf_service import MatriculaPdfService
                    from app.services.matricula_ocr_processor_service import MatriculaOcrProcessorService

                    payload = MatriculaOcrProcessorService.gerar_payload_documentos(
                        db=db,
                        matricula_id=matricula.id,
                    )

                    pdf = MatriculaPdfService.gerar_pdf(
                        imovel_id=imovel.id,
                        dados=payload,
                    )

                    doc_pdf = create_documento_tecnico(
                        db=db,
                        imovel_id=imovel.id,
                        data=DocumentoTecnicoCreate(
                            document_group_key="MATRICULA_PDF",
                            tipo="Matrícula PDF",
                            status_tecnico="EM_ANALISE",
                            arquivo_path=pdf.get("arquivo_path"),
                            metadata_json={
                                "matricula_id": matricula.id,
                                "numero_matricula": matricula.numero_matricula,
                            },
                            gerado_em=datetime.utcnow(),
                        ),
                    )

                    url_pdf = OcrPipelineService._build_file_url(
                        base_url,
                        pdf.get("arquivo_path"),
                    )

                    result["steps"]["matricula_pdf"] = {
                        "success": True,
                        "documento_tecnico_id": doc_pdf.id,
                        "arquivo_path": pdf.get("arquivo_path"),
                        "arquivo_url": url_pdf,
                        "message": "PDF da matrícula gerado.",
                    }

                    result["steps"]["matricula"]["arquivo_path"] = pdf.get("arquivo_path")
                    result["steps"]["matricula"]["arquivo_url"] = url_pdf

                    print(f"✅ PDF matrícula gerado: {pdf.get('arquivo_path')}")

                except Exception as exc_pdf:
                    OcrPipelineService._rollback_safely(db)
                    result["steps"]["matricula_pdf"] = {
                        "success": False,
                        "message": f"Falha ao gerar PDF matrícula: {str(exc_pdf)}",
                    }
                    result["errors"].append(f"Matrícula PDF: {str(exc_pdf)}")
                    print(f"❌ Falha ao gerar PDF matrícula: {str(exc_pdf)}")

            else:
                result["steps"]["matricula"] = {
                    "success": False,
                    "message": "OCR não retornou matrícula.",
                }
                result["errors"].append("OCR não retornou matrícula")

        except Exception as exc:
            OcrPipelineService._rollback_safely(db)
            result["steps"]["matricula"] = {
                "success": False,
                "message": f"Falha ao persistir matrícula: {str(exc)}",
            }
            result["errors"].append(f"Matrícula: {str(exc)}")

         # ================= ANÁLISE =================
        try:
            if matricula and matricula.inteiro_teor:

                dados_analise: dict[str, Any] = {
                    "texto": matricula.inteiro_teor,
                    "numero_matricula": matricula.numero_matricula,
                    "comarca": matricula.comarca,
                    "livro": matricula.livro,
                    "folha": matricula.folha,
                    "codigo_cartorio": matricula.codigo_cartorio,
                    "dados_ocr": dados,
                }

                # =========================================================
                # PROPRIETÁRIOS
                # =========================================================
                try:
                    proprietarios = dados.get("proprietarios")
                    if isinstance(proprietarios, list):
                        dados_analise["proprietarios"] = proprietarios
                except Exception:
                    pass

                # =========================================================
                # CONFRONTANTES (BANCO) — CORRIGIDO
                # =========================================================
                try:
                    confrontantes_formatados: list[dict[str, Any]] = []

                    if confrontantes_db:
                        for c in confrontantes_db:
                            confrontantes_formatados.append(
                                {
                                    "nome": getattr(c, "nome_confrontante", None),
                                    "descricao": getattr(c, "descricao", None),

                                    # 🔥 CORREÇÃO DE MAPEAMENTO
                                    "lado": getattr(c, "lado_label", None),
                                    "lado_normalizado": getattr(c, "direcao_normalizada", None),

                                    "matricula": getattr(c, "matricula_confrontante", None),
                                    "identificacao": getattr(c, "identificacao_imovel_confrontante", None),

                                    # 🔥 NOVOS CAMPOS
                                    "tipo": getattr(c, "tipo", None),
                                    "lote": getattr(c, "lote", None),
                                    "gleba": getattr(c, "gleba", None),
                                }
                            )

                    if confrontantes_formatados:
                        dados_analise["confrontantes"] = confrontantes_formatados

                except Exception:
                    pass

                # =========================================================
                # CONSISTÊNCIA OCR vs DB
                # =========================================================
                try:
                    confrontantes_ocr = dados.get("confrontantes") or []

                    if isinstance(confrontantes_ocr, list):
                        if len(confrontantes_ocr) != len(confrontantes_db):
                            print("⚠️ Divergência OCR vs Banco em confrontantes")
                except Exception:
                    pass

                # =========================================================
                # CHAMADA DA ANÁLISE
                # =========================================================
                analise = MatriculaAnalysisService.analisar(
                    texto=matricula.inteiro_teor,
                    dados_ocr=dados,
                )

                # =========================================================
                # ENRIQUECIMENTO DA ANÁLISE
                # =========================================================
                if isinstance(analise, dict):

                    classificacao = analise.get("classificacao") or {}

                    if dados.get("proprietarios"):
                        classificacao["proprietarios_identificados"] = True

                    if confrontantes_db:
                        classificacao["tem_confrontantes"] = True

                    analise["classificacao"] = classificacao

                    score = analise.get("score_juridico", 0)

                    if dados.get("proprietarios"):
                        score += min(len(dados["proprietarios"]) * 3, 10)

                    if confrontantes_db:
                        score += min(len(confrontantes_db) * 2, 10)

                    if matricula.livro and matricula.folha:
                        score += 5

                    score = min(score, 100)

                    analise["score_juridico"] = score

                result["steps"]["analise_juridica"] = analise

            else:
                result["steps"]["analise_juridica"] = {
                    "success": False,
                    "message": "Matrícula inexistente ou sem inteiro_teor para análise.",
                }

        except Exception as exc:
            OcrPipelineService._rollback_safely(db)
            result["steps"]["analise_juridica"] = {
                "success": False,
                "message": f"Erro na análise jurídica: {str(exc)}",
            }
            result["errors"].append(f"Analise juridica: {str(exc)}")

        # ================= GEOMETRIA =================
        geojson: Optional[str] = None
        geometria: Optional[Geometria] = None
        fonte_geom: Optional[str] = None

        try:
            geojson = OcrPipelineService._resolver_geojson(dados)

            # 🔥 identificar fonte geométrica
            try:
                if isinstance(dados.get("geometria"), dict):
                    fonte_geom = (
                        dados.get("geometria", {}).get("fonte")
                        or ("GEOJSON" if dados.get("geometria", {}).get("geojson") else None)
                        or ("SEGMENTOS" if dados.get("geometria", {}).get("segmentos") else None)
                        or ("MEMORIAL" if dados.get("geometria", {}).get("memorial_texto") else None)
                    )
            except Exception:
                fonte_geom = None

        except Exception as exc:
            OcrPipelineService._rollback_safely(db)
            result["errors"].append(f"Resolver geojson: {str(exc)}")

            # 🔥 fallback seguro
            try:
                if isinstance(dados.get("geometria"), dict):
                    fonte_geom = (
                        dados.get("geometria", {}).get("fonte")
                        or ("GEOJSON" if dados.get("geometria", {}).get("geojson") else None)
                        or ("SEGMENTOS" if dados.get("geometria", {}).get("segmentos") else None)
                        or ("MEMORIAL" if dados.get("geometria", {}).get("memorial_texto") else None)
                    )
            except Exception:
                fonte_geom = None

        if geojson:
            try:
                # =========================================================
                # 🔥 VALIDAÇÃO MÍNIMA DO GEOJSON
                # =========================================================
                geojson_obj = None

                try:
                    geojson_obj = json.loads(geojson) if isinstance(geojson, str) else geojson
                except Exception:
                    geojson_obj = None

                if not isinstance(geojson_obj, dict) or not geojson_obj.get("type"):
                    raise Exception("GeoJSON inválido ou sem campo 'type'")

                # =========================================================
                # 🔥 ANÁLISE DO REFERENCIAL
                # =========================================================
                analise_geo = GeometriaService.analisar_referencial(
                    geojson=geojson,
                    epsg_origem=4326,
                )

                tipo_referencial = str(analise_geo.get("tipo_referencial"))
                epsg_origem = 0 if tipo_referencial == "LOCAL_CARTESIANA" else 4326

                # =========================================================
                # 🔥 CÁLCULO DE ÁREA E PERÍMETRO
                # =========================================================
                epsg_utm, area_ha, perimetro_m = GeometriaService.calcular_area_perimetro(
                    geojson=geojson,
                    epsg_origem=epsg_origem,
                )

                # =========================================================
                # 🔥 PERSISTÊNCIA DA GEOMETRIA
                # =========================================================
                geometria = Geometria(
                    imovel_id=imovel.id,
                    geojson=geojson,
                    epsg_origem=epsg_origem,
                    epsg_utm=epsg_utm,
                    area_hectares=area_ha,
                    perimetro_m=perimetro_m,
                )

                db.add(geometria)
                db.commit()
                db.refresh(geometria)

                # =========================================================
                # 🔥 EXPORTAÇÃO GEOJSON
                # =========================================================
                geo_file = GeometriaService.exportar_geojson(
                    imovel_id=imovel.id,
                    geojson=geometria.geojson,
                )

                # =========================================================
                # 🔥 DOCUMENTO TÉCNICO
                # =========================================================
                doc_geo = create_documento_tecnico(
                    db=db,
                    imovel_id=imovel.id,
                    data=DocumentoTecnicoCreate(
                        document_group_key="GEOMETRIA_GEOJSON",
                        tipo="GeoJSON",
                        status_tecnico="EM_ANALISE",
                        arquivo_path=geo_file.get("arquivo_path"),
                        metadata_json={
                            "geometria_id": geometria.id,
                            "epsg_origem": geometria.epsg_origem,
                            "epsg_utm": geometria.epsg_utm,
                            "fonte_geom": fonte_geom,
                        },
                        gerado_em=datetime.utcnow(),
                    ),
                )

                # =========================================================
                # 🔥 URL FINAL
                # =========================================================
                url_geo = OcrPipelineService._build_file_url(
                    base_url,
                    geo_file.get("arquivo_path"),
                )

                result["steps"]["geometria"] = {
                    "success": True,
                    "geometria_id": geometria.id,
                    "tipo_referencial": tipo_referencial,
                    "epsg_origem": geometria.epsg_origem,
                    "epsg_utm": geometria.epsg_utm,
                    "area_hectares": geometria.area_hectares,
                    "perimetro_m": geometria.perimetro_m,
                    "arquivo_path": geo_file.get("arquivo_path"),
                    "arquivo_url": url_geo,
                    "documento_tecnico_id": doc_geo.id,
                    "fonte": fonte_geom,
                }

            except Exception as exc:
                OcrPipelineService._rollback_safely(db)

                result["steps"]["geometria"] = {
                    "success": False,
                    "message": f"Falha ao gerar geometria: {str(exc)}",
                    "fonte": fonte_geom,
                }

                result["errors"].append(f"Geometria: {str(exc)}")

        else:
            result["steps"]["geometria"] = {
                "success": False,
                "message": "Nenhuma fonte geométrica válida encontrada.",
                "fonte": fonte_geom,
            }

        # =========================================================
        # 🔥 PROCESSAMENTO DE CONFRONTANTES
        # =========================================================
        try:
            from app.services.confrontante_service import ConfrontanteService
            from app.models.confrontante import Confrontante

            confrontantes_raw = dados.get("confrontantes") or []
            confrontantes_processados: list[dict[str, object | None]] = []

            if isinstance(confrontantes_raw, list):

                for index, c in enumerate(confrontantes_raw, start=1):

                    if not isinstance(c, dict):
                        continue

                    # ================= NORMALIZAÇÃO =================
                    lado = OcrPipelineService._normalizar_texto_simples(
                        c.get("lado") or c.get("direcao")
                    )

                    lado_norm = OcrPipelineService._normalizar_texto_simples(
                        c.get("lado_normalizado")
                    )

                    nome = OcrPipelineService._normalizar_texto_simples(
                        c.get("nome")
                    )

                    descricao = OcrPipelineService._normalizar_texto_simples(
                        c.get("descricao")
                    )

                    matricula_cft = OcrPipelineService._normalizar_numero_matricula(
                        c.get("matricula") or c.get("numero_matricula")
                    )

                    identificacao = OcrPipelineService._normalizar_texto_simples(
                        c.get("identificacao")
                    )

                    cpf_cnpj = OcrPipelineService._normalizar_texto_simples(
                        c.get("cpf_cnpj")
                    )

                    tipo = OcrPipelineService._normalizar_texto_simples(
                        c.get("tipo")
                    )

                    lote = OcrPipelineService._normalizar_texto_simples(
                        c.get("lote")
                    )

                    gleba = OcrPipelineService._normalizar_texto_simples(
                        c.get("gleba")
                    )

                    # ================= TEXTO BASE =================
                    texto_base = (
                        descricao
                        or identificacao
                        or nome
                        or (f"MATRÍCULA {matricula_cft}" if matricula_cft else None)
                        or None
                    )

                    # ================= FILTRO =================
                    if not any([
                        lado,
                        lado_norm,
                        nome,
                        descricao,
                        matricula_cft,
                        identificacao,
                        cpf_cnpj,
                        tipo,
                        lote,
                        gleba,
                    ]):
                        continue

                    # ================= GARANTIA DESCRIÇÃO =================
                    if not descricao:
                        descricao = texto_base

                    # ================= PAYLOAD =================
                    confrontantes_processados.append(
                        {
                            "lado": lado,
                            "lado_normalizado": lado_norm,
                            "nome": nome,
                            "descricao": descricao,
                            "matricula": matricula_cft,
                            "identificacao": identificacao,
                            "cpf_cnpj": cpf_cnpj,
                            "tipo": tipo,
                            "lote": lote,
                            "gleba": gleba,
                            "texto_resumo": texto_base,
                        }
                    )

            if confrontantes_processados:
                confrontantes = ConfrontanteService.processar_confrontantes(
                    db=db,
                    imovel=imovel,
                    geometria=geometria,
                    confrontantes_ocr=confrontantes_processados,
                )

                print(f"✅ Confrontantes processados: {len(confrontantes)}")

                try:
                    confrontantes_db = (
                        db.query(Confrontante)
                        .filter(Confrontante.imovel_id == imovel.id)
                        .all()
                    ) or []

                    print(f"📦 Confrontantes carregados do banco: {len(confrontantes_db)}")

                except Exception as exc_db:
                    confrontantes_db = []
                    print(f"⚠️ Falha ao carregar confrontantes do banco: {str(exc_db)}")

                result["steps"]["confrontantes"] = {
                    "success": True,
                    "total": len(confrontantes),
                    "normalizados": len(confrontantes_processados),
                    "persistidos": len(confrontantes_db),
                    "fonte_geom": fonte_geom,
                }

            else:
                confrontantes_db = []

                result["steps"]["confrontantes"] = {
                    "success": False,
                    "total": 0,
                    "normalizados": 0,
                    "persistidos": 0,
                    "message": "Nenhum confrontante válido após normalização.",
                    "fonte_geom": fonte_geom,
                }

                print("⚠️ Nenhum confrontante válido após normalização")

        except Exception as exc:
            OcrPipelineService._rollback_safely(db)

            confrontantes_db = []

            result["steps"]["confrontantes"] = {
                "success": False,
                "message": f"Falha ao processar confrontantes: {str(exc)}",
                "fonte_geom": fonte_geom,
            }

            result["errors"].append(f"Confrontantes: {str(exc)}")

            print(f"❌ Falha confrontantes: {str(exc)}")

        # ================= MEMORIAL =================
        if geometria:
            try:
                # =========================================================
                # CONFRONTANTES DO BANCO → FORMATO DO MEMORIAL
                # =========================================================
                confrontantes_formatados = []

                try:
                    if isinstance(confrontantes_db, list) and confrontantes_db:
                        for c in confrontantes_db:
                            confrontantes_formatados.append(
                                {   "ordem_segmento": getattr(c, "ordem_segmento", None),
                                    "lado_label": getattr(c, "lado_label", None),
                                    "nome": getattr(c, "nome_confrontante", None),
                                    "descricao": getattr(c, "descricao", None),

                                    # 🔥 CORREÇÃO REAL (ALINHADO COM MODEL)
                                    "lado": getattr(c, "lado_label", None),
                                    "lado_normalizado": getattr(c, "direcao_normalizada", None),

                                    "matricula": getattr(c, "matricula_confrontante", None),
                                    "identificacao": getattr(c, "identificacao_imovel_confrontante", None),

                                    # 🔥 CAMPOS COMPLETOS (SEM PERDA)
                                    "cpf_cnpj": getattr(c, "cpf_cnpj", None),  # pode não existir → ok
                                    "tipo": getattr(c, "tipo", None),
                                    "lote": getattr(c, "lote", None),
                                    "gleba": getattr(c, "gleba", None),
                                }
                            )
                except Exception:
                    confrontantes_formatados = []

                # =========================================================
                # DADOS AUXILIARES DO IMÓVEL
                # =========================================================
                nome_imovel = None

                try:
                    nome_imovel = getattr(imovel, "nome", None)
                except Exception:
                    nome_imovel = None

                # =========================================================
                # GERAÇÃO DO MEMORIAL
                # =========================================================
                memorial = MemorialService.gerar_memorial(
                    geometria_id=geometria.id,
                    geojson=geometria.geojson,
                    epsg_origem=geometria.epsg_origem,
                    area_hectares=geometria.area_hectares or 0,
                    perimetro_m=geometria.perimetro_m or 0,
                    imovel_id=imovel.id,
                    confrontantes=confrontantes_formatados,
                    nome_imovel=nome_imovel,
                )

                memorial_json = OcrPipelineService._json_safe(memorial)
                memorial_texto = str(memorial.get("texto_preview") or "").strip()

                if not memorial_texto:
                    raise ValueError("Memorial gerado sem texto_preview.")

                # =========================================================
                # DOCUMENTO TÉCNICO
                # =========================================================
                doc_memorial = create_documento_tecnico(
                    db=db,
                    imovel_id=imovel.id,
                    data=DocumentoTecnicoCreate(
                        document_group_key="MEMORIAL_DESCRITIVO",
                        tipo="Memorial Descritivo",
                        status_tecnico="EM_ANALISE",
                        conteudo_texto=memorial_texto,
                        conteudo_json=memorial_json,
                        metadata_json={
                            "geometria_id": geometria.id,
                            "epsg_origem": geometria.epsg_origem,
                            "epsg_utm": memorial.get("epsg_utm"),
                            "tipo_referencial": memorial.get("tipo_referencial"),
                            "arquivo_path": memorial.get("arquivo_path"),
                            "arquivo_url": memorial.get("arquivo_url"),
                            "fonte_geom": fonte_geom,
                            "total_confrontantes": len(confrontantes_formatados),
                            "nome_imovel": nome_imovel,
                        },
                        arquivo_path=memorial.get("arquivo_path"),
                        arquivo_url=memorial.get("arquivo_url"),
                        gerado_em=datetime.utcnow(),
                    ),
                )

                result["steps"]["memorial"] = {
                    "success": True,
                    "documento_tecnico_id": doc_memorial.id,
                    "texto_preview": memorial_texto[:4000],
                    "arquivo_path": memorial.get("arquivo_path"),
                    "arquivo_url": memorial.get("arquivo_url"),
                    "tipo_referencial": memorial.get("tipo_referencial"),
                    "epsg_utm": memorial.get("epsg_utm"),
                    "fonte": fonte_geom,
                    "total_confrontantes": len(confrontantes_formatados),
                    "message": "Memorial gerado com arquivo.",
                }

            except Exception as exc:
                OcrPipelineService._rollback_safely(db)

                result["steps"]["memorial"] = {
                    "success": False,
                    "message": f"Falha ao gerar memorial: {str(exc)}",
                    "fonte": fonte_geom,
                }

                result["errors"].append(f"Memorial: {str(exc)}")

        else:
            result["steps"]["memorial"] = {
                "success": False,
                "skipped": True,
                "message": "Memorial não executado: geometria inexistente.",
                "fonte": fonte_geom,
            }

        # =========================================================
        # CROQUI
        # =========================================================
        if geometria:
            try:
                # =========================================================
                # CONFRONTANTES DO BANCO (PADRÃO CORRETO DO PIPELINE)
                # =========================================================
                confrontantes_formatados = []

                try:
                    if isinstance(confrontantes_db, list) and confrontantes_db:
                        for c in confrontantes_db:
                            confrontantes_formatados.append(
                                {
                                    "nome": getattr(c, "nome_confrontante", None),
                                    "descricao": getattr(c, "descricao", None),

                                    # 🔥 CORREÇÃO REAL
                                    "lado": getattr(c, "lado_label", None),
                                    "lado_normalizado": getattr(c, "direcao_normalizada", None),

                                    "matricula": getattr(c, "matricula_confrontante", None),
                                    "identificacao": getattr(c, "identificacao_imovel_confrontante", None),

                                    # 🔥 CAMPOS COMPLETOS
                                    "cpf_cnpj": getattr(c, "cpf_cnpj", None),
                                    "tipo": getattr(c, "tipo", None),
                                    "lote": getattr(c, "lote", None),
                                    "gleba": getattr(c, "gleba", None),
                                }
                            )
                except Exception:
                    confrontantes_formatados = []

                # =========================================================
                # GERAÇÃO DO SVG
                # =========================================================
                svg = CroquiService.gerar_svg(
                    geometria.geojson,
                    confrontantes=confrontantes_formatados,
                )

                # =========================================================
                # PERSISTÊNCIA EM DISCO
                # =========================================================
                folder = f"app/uploads/imoveis/{imovel.id}/croqui"
                os.makedirs(folder, exist_ok=True)

                path_svg = f"{folder}/croqui_{geometria.id}.svg"

                with open(path_svg, "w", encoding="utf-8") as f:
                    f.write(svg)

                # =========================================================
                # URL
                # =========================================================
                url_svg = OcrPipelineService._build_file_url(base_url, path_svg)

                # =========================================================
                # DOCUMENTO TÉCNICO
                # =========================================================
                doc_croqui = create_documento_tecnico(
                    db=db,
                    imovel_id=imovel.id,
                    data=DocumentoTecnicoCreate(
                        document_group_key="CROQUI",
                        tipo="Croqui",
                        status_tecnico="EM_ANALISE",
                        arquivo_path=path_svg,
                        metadata_json={
                            "geometria_id": geometria.id,
                            "confrontantes_incluidos": bool(confrontantes_formatados),
                            "total_confrontantes": len(confrontantes_formatados),
                            "fonte_geom": fonte_geom,
                        },
                        gerado_em=datetime.utcnow(),
                    ),
                )

                result["steps"]["croqui"] = {
                    "success": True,
                    "arquivo_path": path_svg,
                    "arquivo_url": url_svg,
                    "documento_tecnico_id": doc_croqui.id,
                    "confrontantes_incluidos": bool(confrontantes_formatados),
                    "total_confrontantes": len(confrontantes_formatados),
                    "fonte": fonte_geom,
                    "message": f"Croqui salvo: {path_svg}",
                }

                print(f"✅ Croqui salvo: {path_svg}")

            except Exception as exc:
                OcrPipelineService._rollback_safely(db)

                result["steps"]["croqui"] = {
                    "success": False,
                    "message": f"Falha ao gerar croqui: {str(exc)}",
                }

                result["errors"].append(f"Croqui: {str(exc)}")

                print(f"❌ Falha ao gerar croqui: {str(exc)}")

        else:
            result["steps"]["croqui"] = {
                "success": False,
                "skipped": True,
                "message": "Croqui não executado: geometria inexistente.",
                "fonte": fonte_geom,
            }

        # =========================================================
        # CAD / SCR
        # =========================================================
        if geometria:
            try:
                scr = CadExportService.gerar_scr(geometria.geojson)

                path_scr = CadExportService.salvar_scr(
                    imovel_id=imovel.id,
                    scr=scr,
                )

                url_scr = OcrPipelineService._build_file_url(base_url, path_scr)

                doc_cad = create_documento_tecnico(
                    db=db,
                    imovel_id=imovel.id,
                    data=DocumentoTecnicoCreate(
                        document_group_key="CAD_SCRIPT",
                        tipo="Script CAD",
                        status_tecnico="EM_ANALISE",
                        arquivo_path=path_scr,
                        metadata_json={
                            "geometria_id": geometria.id,
                            "formato": "SCR",
                            "fonte_geom": fonte_geom,  # 🔥 NOVO
                        },
                        gerado_em=datetime.utcnow(),
                    ),
                )

                result["steps"]["cad"] = {
                    "success": True,
                    "arquivo_path": path_scr,
                    "arquivo_url": url_scr,
                    "documento_tecnico_id": doc_cad.id,
                    "fonte": fonte_geom,  # 🔥 NOVO
                    "message": f"Script CAD salvo: {path_scr}",
                }

                print(f"✅ Script CAD salvo: {path_scr}")

            except Exception as exc:
                OcrPipelineService._rollback_safely(db)
                result["steps"]["cad"] = {
                    "success": False,
                    "message": f"Falha ao gerar CAD: {str(exc)}",
                }
                result["errors"].append(f"CAD: {str(exc)}")
                print(f"❌ Falha ao gerar CAD: {str(exc)}")
        else:
            result["steps"]["cad"] = {
                "success": False,
                "skipped": True,
                "message": "CAD não executado: geometria inexistente.",
                "fonte": fonte_geom,
            }

        # =========================================================
        # TXT (LISP / COORDENADAS / PERÍMETRO)
        # =========================================================
        if geometria:
            try:
                from app.services.txt_lisp_service import TxtLispService

                # =====================================================
                # DADOS AUXILIARES
                # =====================================================
                numero_matricula_txt = (
                    matricula.numero_matricula
                    if matricula
                    else None
                )

                descricao_imovel_txt = (
                    dados.get("descricao_imovel")
                    or (
                        (dados.get("imovel") or {}).get("descricao")
                        if isinstance(dados.get("imovel"), dict)
                        else None
                    )
                    or getattr(imovel, "descricao", None)
                    or getattr(geometria, "nome", None)
                    or (
                        matricula.numero_matricula
                        if matricula
                        else None
                    )
                    or getattr(imovel, "nome", None)
                    or "IMOVEL"
                )

                # =====================================================
                # TXT ÚNICO PROFISSIONAL
                #
                # Mantém a chave histórica "txt" no resultado, mas o
                # arquivo passa a consolidar todos os polígonos em um
                # único TXT no padrão LISP exigido pelo cliente.
                # =====================================================
                geometrias_txt = [geometria]

                poligonos_txt: list[dict[str, Any]] = []
                for index, geom_txt in enumerate(geometrias_txt, start=1):
                    nome_poligono = (
                        getattr(geom_txt, "nome", None)
                        or descricao_imovel_txt
                        or (
                            f"Matrícula {numero_matricula_txt}"
                            if numero_matricula_txt
                            else None
                        )
                        or f"IMOVEL {imovel.id}"
                    )

                    if numero_matricula_txt and numero_matricula_txt not in str(nome_poligono):
                        nome_poligono = f"{nome_poligono} - Matrícula {numero_matricula_txt}"

                    if len(geometrias_txt) > 1 and index > 1:
                        nome_poligono = f"{nome_poligono} - Polígono {index}"

                    poligonos_txt.append(
                        {
                            "geojson": geom_txt.geojson,
                            "nome_poligono": nome_poligono,
                            "epsg_origem": getattr(geom_txt, "epsg_origem", None) or 4326,
                            "geometria_id": geom_txt.id,
                        }
                    )

                txt = TxtLispService.gerar_txt_lisp(
                    poligonos=poligonos_txt,
                )

                path_txt = TxtLispService.salvar_txt(
                    imovel_id=imovel.id,
                    txt=txt,
                )

                url_txt = OcrPipelineService._build_file_url(
                    base_url,
                    path_txt,
                )

                doc_txt = create_documento_tecnico(
                    db=db,
                    imovel_id=imovel.id,
                    data=DocumentoTecnicoCreate(
                        document_group_key="COORDENADAS_TXT",
                        tipo="TXT Perímetros/LISP",
                        status_tecnico="EM_ANALISE",
                        conteudo_texto=txt,
                        arquivo_path=path_txt,
                        metadata_json={
                            "geometria_id": geometria.id,
                            "geometrias_ids": [
                                item.get("geometria_id")
                                for item in poligonos_txt
                            ],
                            "formato": "TXT",
                            "tipo_exportacao": "PERIMETROS_LISP_CAD",
                            "nome_poligono": poligonos_txt[0].get("nome_poligono"),
                            "numero_matricula": numero_matricula_txt,
                            "total_poligonos": len(poligonos_txt),
                            "fonte_geom": fonte_geom,
                        },
                        gerado_em=datetime.utcnow(),
                    ),
                )

                # =====================================================
                # RESULTADO FINAL
                # =====================================================
                result["steps"]["txt"] = {
                    "success": True,

                    # ================================================
                    # TXT COORDENADAS
                    # ================================================
                    "arquivo_path": path_txt,
                    "arquivo_url": url_txt,
                    "documento_tecnico_id": doc_txt.id,

                    # ================================================
                    # METADADOS
                    # ================================================
                    "nome_poligono": poligonos_txt[0].get("nome_poligono"),
                    "total_poligonos": len(poligonos_txt),
                    "numero_matricula": numero_matricula_txt,
                    "fonte": fonte_geom,

                    "message": (
                        "TXT único de perímetros/LISP gerado."
                    ),
                }

                # Compatibilidade com consumidores antigos:
                # estes campos continuam existindo, mas apontam para o
                # mesmo arquivo único.
                result["steps"]["txt"].update(
                    {
                        "arquivo_perimetro_path": path_txt,
                        "arquivo_perimetro_url": url_txt,
                        "documento_tecnico_perimetro_id": doc_txt.id,
                        "arquivo_lisp_path": path_txt,
                        "arquivo_lisp_url": url_txt,
                        "documento_tecnico_lisp_id": doc_txt.id,
                    }
                )

                print(
                    f"✅ TXT único perímetros/LISP gerado: {path_txt}"
                )

            except Exception as exc:
                OcrPipelineService._rollback_safely(db)

                result["steps"]["txt"] = {
                    "success": False,
                    "message": (
                        f"Falha ao gerar TXT: {str(exc)}"
                    ),
                }

                result["errors"].append(
                    f"TXT: {str(exc)}"
                )

                print(
                    f"❌ Falha ao gerar TXT: {str(exc)}"
                )

        else:
            result["steps"]["txt"] = {
                "success": False,
                "skipped": True,
                "message": (
                    "TXT não executado: "
                    "geometria inexistente."
                ),
                "fonte": fonte_geom,
            }

        # =========================================================
        # DXF
        # =========================================================
        if geometria:
            try:
                from app.services.dxf_export_service import DxfExportService

                # =========================================================
                # CONFRONTANTES DO BANCO (PADRÃO COMPLETO DO PIPELINE)
                # =========================================================
                confrontantes_formatados = []

                try:

                    if isinstance(confrontantes_db, list) and confrontantes_db:

                        for c in confrontantes_db:

                            confrontantes_formatados.append(
                                {
                                    # =====================================================
                                    # IDENTIFICAÇÃO PRINCIPAL
                                    # =====================================================
                                    "nome": getattr(
                                        c,
                                        "nome_confrontante",
                                        None,
                                    ),

                                    "descricao": getattr(
                                        c,
                                        "descricao",
                                        None,
                                    ),

                                    # =====================================================
                                    # DIREÇÃO
                                    # =====================================================
                                    "lado": getattr(
                                        c,
                                        "lado_label",
                                        None,
                                    ),

                                    "lado_normalizado": getattr(
                                        c,
                                        "direcao_normalizada",
                                        None,
                                    ),

                                    # =====================================================
                                    # MATRÍCULA / IDENTIFICAÇÃO
                                    # =====================================================
                                    "matricula": getattr(
                                        c,
                                        "matricula_confrontante",
                                        None,
                                    ),

                                    "identificacao": getattr(
                                        c,
                                        "identificacao_imovel_confrontante",
                                        None,
                                    ),

                                    # =====================================================
                                    # DADOS COMPLEMENTARES
                                    # =====================================================
                                    "cpf_cnpj": getattr(
                                        c,
                                        "cpf_cnpj",
                                        None,
                                    ),

                                    "tipo": getattr(
                                        c,
                                        "tipo",
                                        None,
                                    ),

                                    "lote": getattr(
                                        c,
                                        "lote",
                                        None,
                                    ),

                                    "gleba": getattr(
                                        c,
                                        "gleba",
                                        None,
                                    ),
                                }
                            )

                except Exception:
                    confrontantes_formatados = []

                # =========================================================
                # GERAÇÃO DO DXF COM CONTEXTO COMPLETO
                # =========================================================
                doc_dxf_file = DxfExportService.gerar_dxf(
                    geometria.geojson,
                    confrontantes=confrontantes_formatados,
                )

                path_dxf = DxfExportService.salvar_dxf(
                    imovel_id=imovel.id,
                    doc=doc_dxf_file,
                )

                url_dxf = OcrPipelineService._build_file_url(base_url, path_dxf)

                doc_dxf = create_documento_tecnico(
                    db=db,
                    imovel_id=imovel.id,
                    data=DocumentoTecnicoCreate(
                        document_group_key="DXF",
                        tipo="Arquivo DXF",
                        status_tecnico="EM_ANALISE",
                        arquivo_path=path_dxf,
                        metadata_json={
                            "geometria_id": geometria.id,
                            "formato": "DXF",
                            "total_confrontantes": len(confrontantes_formatados),
                            "fonte_geom": fonte_geom,  # 🔥 NOVO
                        },
                        gerado_em=datetime.utcnow(),
                    ),
                )

                result["steps"]["dxf"] = {
                    "success": True,
                    "arquivo_path": path_dxf,
                    "arquivo_url": url_dxf,
                    "documento_tecnico_id": doc_dxf.id,
                    "total_confrontantes": len(confrontantes_formatados),
                    "fonte": fonte_geom,  # 🔥 NOVO
                    "message": f"DXF gerado: {path_dxf}",
                }

                print(f"✅ DXF gerado: {path_dxf}")

            except Exception as exc:
                OcrPipelineService._rollback_safely(db)
                result["steps"]["dxf"] = {
                    "success": False,
                    "message": f"Falha ao gerar DXF: {str(exc)}",
                }
                result["errors"].append(f"DXF: {str(exc)}")
                print(f"❌ Falha ao gerar DXF: {str(exc)}")
        else:
            result["steps"]["dxf"] = {
                "success": False,
                "skipped": True,
                "message": "DXF não executado: geometria inexistente.",
                "fonte": fonte_geom,
            }

        # =========================================================
        # SHP (QGIS READY + VALIDAÇÃO TOPOLOGICA)
        # =========================================================
        if geometria:
            try:
                from app.services.shp_export_service import ShpExportService

                gdf = ShpExportService.gerar_shp(geometria.geojson)

                path_folder = ShpExportService.salvar_shp(
                    imovel_id=imovel.id,
                    gdf=gdf,
                )

                # 🔥 proteção adicional
                if not os.path.exists(path_folder):
                    raise Exception("Pasta SHP não foi criada corretamente")

                arquivos = os.listdir(path_folder)

                shp_file = next(
                    (f for f in arquivos if f.lower().endswith(".shp")),
                    None
                )

                if not shp_file:
                    raise Exception("Arquivo .shp não encontrado na pasta gerada")

                arquivo_path = f"{path_folder}/{shp_file}"

                arquivo_url = OcrPipelineService._build_file_url(
                    base_url,
                    arquivo_path,
                )

                doc_shp = create_documento_tecnico(
                    db=db,
                    imovel_id=imovel.id,
                    data=DocumentoTecnicoCreate(
                        document_group_key="SHP",
                        tipo="Shapefile",
                        status_tecnico="EM_ANALISE",
                        arquivo_path=arquivo_path,
                        metadata_json={
                            "geometria_id": geometria.id,
                            "formato": "SHP",
                            "pasta_path": path_folder,
                            "fonte_geom": fonte_geom,  # 🔥 NOVO
                        },
                        gerado_em=datetime.utcnow(),
                    ),
                )

                result["steps"]["shp"] = {
                    "success": True,
                    "pasta_path": path_folder,
                    "arquivo_path": arquivo_path,
                    "arquivo_url": arquivo_url,
                    "documento_tecnico_id": doc_shp.id,
                    "fonte": fonte_geom,  # 🔥 NOVO
                    "message": f"SHP gerado: {arquivo_path}",
                }

                print(f"✅ SHP gerado: {arquivo_path}")

            except Exception as exc:
                OcrPipelineService._rollback_safely(db)

                result["steps"]["shp"] = {
                    "success": False,
                    "message": f"Falha ao gerar SHP: {str(exc)}",
                }

                result["errors"].append(f"SHP: {str(exc)}")

                print(f"❌ Falha ao gerar SHP: {str(exc)}")

        else:
            result["steps"]["shp"] = {
                "success": False,
                "skipped": True,
                "message": "SHP não executado: geometria inexistente.",
                "fonte": fonte_geom,
            }

        # =========================================================
        # SIGEF CSV
        # =========================================================
        if geometria:
            if geometria.epsg_origem and geometria.epsg_origem > 0:
                try:
                    payload = SigefCsvExportRequest(
                        geometria_id=geometria.id,
                        prefixo_vertice="V",
                        document_group_key="PLANILHA_SIGEF",
                        tipo="Planilha SIGEF",
                        observacoes_tecnicas=None,
                        incluir_conteudo=False,
                    )

                    sigef_data = exportar_sigef_csv(db, payload)

                    if not isinstance(sigef_data, dict):
                        raise Exception("Retorno inválido ao gerar SIGEF CSV")

                    path_sigef = sigef_data.get("arquivo_path")
                    documento_tecnico_id = sigef_data.get("documento_tecnico_id")

                    if not path_sigef:
                        raise Exception("SIGEF CSV gerado sem arquivo_path")

                    url_sigef = OcrPipelineService._build_file_url(
                        base_url,
                        path_sigef,
                    )

                    if not documento_tecnico_id:
                        doc_sigef = create_documento_tecnico(
                            db=db,
                            imovel_id=imovel.id,
                            data=DocumentoTecnicoCreate(
                                document_group_key="PLANILHA_SIGEF",
                                tipo="Planilha SIGEF",
                                status_tecnico="EM_ANALISE",
                                arquivo_path=path_sigef,
                                metadata_json={
                                    "geometria_id": geometria.id,
                                    "epsg_utm": sigef_data.get("epsg_utm"),
                                    "epsg_origem": geometria.epsg_origem,
                                    "fonte_geom": fonte_geom,
                                },
                                gerado_em=datetime.utcnow(),
                            ),
                        )
                        documento_tecnico_id = doc_sigef.id

                    result["steps"]["sigef_csv"] = {
                        "success": True,
                        "documento_tecnico_id": documento_tecnico_id,
                        "arquivo_path": path_sigef,
                        "arquivo_url": url_sigef,
                        "epsg_utm": sigef_data.get("epsg_utm"),
                        "epsg_origem": geometria.epsg_origem,
                        "fonte": fonte_geom,
                        "message": "Planilha SIGEF gerada com sucesso.",
                    }

                    print(f"[SIGEF] ✅ Planilha SIGEF gerada: {path_sigef}")

                except Exception as exc:
                    OcrPipelineService._rollback_safely(db)

                    result["steps"]["sigef_csv"] = {
                        "success": False,
                        "message": f"Falha ao gerar SIGEF CSV: {str(exc)}",
                    }

                    result["errors"].append(f"SIGEF CSV: {str(exc)}")

                    print(f"[SIGEF] ❌ Falha ao gerar SIGEF CSV: {str(exc)}")

            else:
                result["steps"]["sigef_csv"] = {
                    "success": False,
                    "skipped": True,
                    "message": (
                        "SIGEF CSV não executado: geometria local/cartesiana "
                        "não é exportável como SIGEF oficial."
                    ),
                    "fonte": fonte_geom,
                }

                print("[SIGEF] ℹ️ Ignorado: geometria local/cartesiana")

        else:
            result["steps"]["sigef_csv"] = {
                "success": False,
                "skipped": True,
                "message": "SIGEF CSV não executado: geometria inexistente.",
                "fonte": fonte_geom,
            }
        # =========================================================
        # SUCESSO FINAL
        # =========================================================
        steps = result.get("steps", {})

        geometria_ok = bool((steps.get("geometria") or {}).get("success"))
        memorial_ok = bool((steps.get("memorial") or {}).get("success"))
        croqui_ok = bool((steps.get("croqui") or {}).get("success"))
        cad_ok = bool((steps.get("cad") or {}).get("success"))
        sigef_ok = bool((steps.get("sigef_csv") or {}).get("success"))

        epsg_origem_atual = geometria.epsg_origem if geometria else None

        # 🔥 NOVO — QUALIDADE OCR
        qualidade_ocr = dados.get("qualidade") if isinstance(dados, dict) else None

        score_ocr = 0
        confianca_geral = None

        if isinstance(qualidade_ocr, dict):
            try:
                score_ocr = int(qualidade_ocr.get("score", 0) or 0)
            except Exception:
                score_ocr = 0

            confianca_geral = qualidade_ocr.get("confianca_geral")

        # 🔥 NOVO — CONTROLE DE SIGEF
        sigef_obrigatorio = bool(
            geometria
            and epsg_origem_atual
            and epsg_origem_atual > 0
        )

        # 🔥 REGRAS DE SUCESSO
        sucesso_base = (
            geometria_ok
            and memorial_ok
            and croqui_ok
            and cad_ok
        )

        if sigef_obrigatorio:
            sucesso_base = sucesso_base and sigef_ok

        # =========================================================
        # 🔥 QUALIDADE OCR (NÃO BLOQUEANTE)
        # =========================================================
        qualidade_minima_ok = score_ocr >= 60

        if not qualidade_minima_ok:

            warnings = result.get("warnings")

            if not isinstance(warnings, list):
                warnings = []
                result["warnings"] = warnings

            warnings.append(
                (
                    "OCR com score reduzido "
                    f"(score={score_ocr}), porém pipeline permaneceu executável."
                )
            )

        # =========================================================
        # 🔥 SUCESSO FINAL REAL
        # =========================================================
        result["success"] = sucesso_base

        # 🔥 DEBUG / RASTREABILIDADE
        result["validacao_pipeline"] = {
            "geometria_ok": geometria_ok,
            "memorial_ok": memorial_ok,
            "croqui_ok": croqui_ok,
            "cad_ok": cad_ok,
            "sigef_obrigatorio": sigef_obrigatorio,
            "sigef_ok": sigef_ok,
            "qualidade_score": score_ocr,
            "qualidade_minima_ok": qualidade_minima_ok,
            "confianca_geral": confianca_geral,
        }

        print("🏁 Pipeline OCR concluído")
        

        return result

    @staticmethod
    def _normalizar_texto_simples(valor: Any) -> Optional[str]:
        if valor is None:
            return None

        texto = str(valor).strip()

        if not texto:
            return None

        return " ".join(texto.split())


    @staticmethod
    def _normalizar_numero_matricula(valor: Any) -> Optional[str]:
        if valor is None:
            return None

        # 🔥 reutiliza normalização base
        texto = OcrPipelineService._normalizar_texto_simples(valor)

        if not texto:
            return None

        # 🔥 remove termos comuns com boundary (evita remoção indevida)
        texto = re.sub(
            r"\b(matr[ií]cula|mat\.?|registro|n[º°o]|sob\s*n[º°o])\b",
            "",
            texto,
            flags=re.IGNORECASE,
        )

        # 🔥 remove tudo que não for padrão de matrícula
        texto = re.sub(r"[^\d./-]", "", texto)

        texto = texto.strip()

        # 🔥 fallback de segurança
        if not texto:
            return None

        return texto
    
    @staticmethod
    def _upsert_matricula(
        db: Session,
        imovel: Imovel,
        dados: dict[str, Any],
    ) -> Optional[Matricula]:
        numero_matricula: Optional[str] = None

        # =========================================================
        # 🔥 NORMALIZAÇÃO DO PAYLOAD
        # =========================================================
        matricula_payload = dados.get("matricula")
        if not isinstance(matricula_payload, dict):
            matricula_payload = {}

        # =========================================================
        # 🔥 PRIORIDADE CORRETA DE EXTRAÇÃO
        # =========================================================
        numero_matricula = (
            matricula_payload.get("numero")
            or dados.get("numero_matricula")
            or (
                dados.get("matricula")
                if not isinstance(dados.get("matricula"), dict)
                else None
            )
        )

        # =========================================================
        # 🔥 FALLBACK PELO TEXTO INTEGRAL OCR
        # =========================================================
        if not numero_matricula:

            texto_integral = " ".join(
                [
                    str(dados.get("texto") or ""),
                    str(dados.get("texto_extraido") or ""),
                    str(dados.get("inteiro_teor") or ""),
                    str(dados.get("conteudo") or ""),
                ]
            )

            texto_integral = " ".join(texto_integral.split())

            regex_matriculas = [

                # =====================================================
                # MATRÍCULA Nº 12.345
                # =====================================================
                r"(?:MATR[IÍ]CULA\s*(?:N[º°O.]*)?\s*)(\d{1,3}(?:\.\d{3})+|\d+)",

                # =====================================================
                # SOB Nº 12.345
                # =====================================================
                r"(?:SOB\s*(?:N[º°O.]*)?\s*)(\d{1,3}(?:\.\d{3})+|\d+)",

                # =====================================================
                # M-12.345
                # =====================================================
                r"\bM[-\s]?(\d{1,3}(?:\.\d{3})+|\d+)\b",

                # =====================================================
                # MATRÍCULA: 12345
                # =====================================================
                r"(?:MATR[IÍ]CULA[:\s]*)(\d+)",

                # =====================================================
                # LIVRO/FICHA
                # =====================================================
                r"(?:FICHA|LIVRO)[^\d]{0,20}(\d{1,3}(?:\.\d{3})+|\d+)",
            ]

            for pattern in regex_matriculas:

                try:

                    match = re.search(
                        pattern,
                        texto_integral,
                        flags=re.IGNORECASE,
                    )

                    if match:

                        candidato = match.group(1)

                        candidato = OcrPipelineService._normalizar_numero_matricula(
                            candidato
                        )

                        if candidato:
                            numero_matricula = candidato
                            break

                except Exception:
                    continue

        # =========================================================
        # 🔥 NORMALIZAÇÃO FINAL
        # =========================================================
        numero_matricula = OcrPipelineService._normalizar_numero_matricula(
            numero_matricula
        )

        # =========================================================
        # 🔴 VALIDAÇÃO FINAL
        # =========================================================
        if not numero_matricula:
            return None

        # =========================================================
        # 🔥 RESOLVER CARTÓRIO (INTEGRAÇÃO COM BANCO)
        # =========================================================
        try:
            cartorio_id = MatriculaOcrProcessorService._resolver_cartorio(
                db,
                dados,
            )
        except Exception:
            cartorio_id = None

        # =========================================================
        # 🔥 CAMPOS NORMALIZADOS
        # =========================================================
        livro: Optional[str] = OcrPipelineService._normalizar_texto_simples(
            dados.get("livro") or matricula_payload.get("livro")
        )

        folha: Optional[str] = OcrPipelineService._normalizar_texto_simples(
            dados.get("folha") or matricula_payload.get("folha")
        )

        comarca: Optional[str] = OcrPipelineService._normalizar_texto_simples(
            dados.get("comarca") or matricula_payload.get("comarca")
        )

        cartorio: Optional[str] = OcrPipelineService._normalizar_texto_simples(
            dados.get("cartorio") or matricula_payload.get("cartorio")
        )

        codigo_cartorio: Optional[str] = OcrPipelineService._normalizar_texto_simples(
            dados.get("codigo_cartorio")
            or dados.get("codigo_cartorio_id")
            or dados.get("codigo")
        )

        descricao_imovel: Optional[str] = OcrPipelineService._normalizar_texto_simples(
            dados.get("descricao_imovel")
            or (dados.get("imovel") or {}).get("descricao")
        )

        observacoes: Optional[str] = OcrPipelineService._normalizar_texto_simples(
            dados.get("observacoes")
        )

        proprietarios = dados.get("proprietarios")
        confrontantes = dados.get("confrontantes")

        # =========================================================
        # 🔥 MONTAGEM DO INTEIRO TEOR
        # =========================================================
        inteiro_teor_partes: list[str] = []

        if descricao_imovel:
            inteiro_teor_partes.append(
                f"DESCRIÇÃO DO IMÓVEL: {descricao_imovel}"
            )

        if comarca:
            inteiro_teor_partes.append(
                f"COMARCA: {comarca}"
            )

        if cartorio:
            inteiro_teor_partes.append(
                f"CARTÓRIO: {cartorio}"
            )

        if livro:
            inteiro_teor_partes.append(
                f"LIVRO: {livro}"
            )

        if folha:
            inteiro_teor_partes.append(
                f"FOLHA: {folha}"
            )

        # =========================================================
        # 🔥 PROPRIETÁRIOS
        # =========================================================
        if isinstance(proprietarios, list) and proprietarios:
            inteiro_teor_partes.append("PROPRIETÁRIOS:")

            for item in proprietarios:
                if not isinstance(item, dict):
                    continue

                nome = OcrPipelineService._normalizar_texto_simples(item.get("nome"))
                cpf_cnpj = OcrPipelineService._normalizar_texto_simples(item.get("cpf_cnpj"))
                tipo = OcrPipelineService._normalizar_texto_simples(item.get("tipo"))

                if not nome:
                    continue

                partes_linha: list[str] = [nome]

                if cpf_cnpj:
                    partes_linha.append(f"CPF/CNPJ: {cpf_cnpj}")

                if tipo:
                    partes_linha.append(f"Tipo: {tipo}")

                inteiro_teor_partes.append("- " + " | ".join(partes_linha))

        # =========================================================
        # 🔥 CONFRONTANTES
        # =========================================================
        if isinstance(confrontantes, list) and confrontantes:
            inteiro_teor_partes.append("CONFRONTANTES:")

            for item in confrontantes:
                if not isinstance(item, dict):
                    continue

                # =========================================================
                # 🔥 NORMALIZAÇÃO COMPLETA (ALINHADA COM PIPELINE)
                # =========================================================
                direcao = OcrPipelineService._normalizar_texto_simples(
                    item.get("lado_normalizado")
                    or item.get("direcao")
                    or item.get("lado")
                )

                nome = OcrPipelineService._normalizar_texto_simples(
                    item.get("nome")
                )

                descricao = OcrPipelineService._normalizar_texto_simples(
                    item.get("descricao")
                )

                matricula_confrontante = OcrPipelineService._normalizar_numero_matricula(
                    item.get("matricula") or item.get("numero_matricula")
                )

                identificacao = OcrPipelineService._normalizar_texto_simples(
                    item.get("identificacao")
                )

                tipo = OcrPipelineService._normalizar_texto_simples(
                    item.get("tipo")
                )

                lote = OcrPipelineService._normalizar_texto_simples(
                    item.get("lote")
                )

                gleba = OcrPipelineService._normalizar_texto_simples(
                    item.get("gleba")
                )

                cpf_cnpj = OcrPipelineService._normalizar_texto_simples(
                    item.get("cpf_cnpj")
                )

                # =========================================================
                # 🔥 GARANTIA DE DIREÇÃO (CRÍTICO)
                # =========================================================
                if not direcao:
                    direcao = "NÃO INFORMADO"

                # =========================================================
                # 🔴 FILTRO INTELIGENTE
                # =========================================================
                if not any([
                    nome,
                    descricao,
                    matricula_confrontante,
                    identificacao,
                    tipo,
                    lote,
                    gleba,
                    cpf_cnpj,
                    direcao,
                ]):
                    continue

                # =========================================================
                # 🔥 MONTAGEM PROFISSIONAL DO TEXTO
                # =========================================================
                partes_linha: list[str] = []

                if direcao:
                    partes_linha.append(
                        f"DIREÇÃO: {direcao}"
                    )

                if nome:
                    partes_linha.append(
                        f"NOME: {nome}"
                    )

                if matricula_confrontante:
                    partes_linha.append(
                        f"MATRÍCULA: {matricula_confrontante}"
                    )

                if identificacao:
                    partes_linha.append(
                        f"IMÓVEL: {identificacao}"
                    )

                if lote:
                    partes_linha.append(
                        f"LOTE: {lote}"
                    )

                if gleba:
                    partes_linha.append(
                        f"GLEBA: {gleba}"
                    )

                if tipo:
                    partes_linha.append(
                        f"TIPO: {tipo}"
                    )

                if cpf_cnpj:
                    partes_linha.append(
                        f"CPF/CNPJ: {cpf_cnpj}"
                    )

                if descricao:
                    partes_linha.append(
                        f"DESCRIÇÃO: {descricao}"
                    )

                # =========================================================
                # 🔥 CORREÇÃO CRÍTICA DE RENDERIZAÇÃO (PDF / WEASYPRINT)
                # =========================================================
                if partes_linha:
                    inteiro_teor_partes.append(
                        "- " + "<br/>".join(partes_linha)
                    )

        # =========================================================
        # 🔥 OBSERVAÇÕES
        # =========================================================
        if observacoes:
            inteiro_teor_partes.append(
                f"OBSERVAÇÕES: {observacoes}"
            )

        # =========================================================
        # 🔥 CONSOLIDAÇÃO DO INTEIRO TEOR
        # =========================================================
        inteiro_teor_montado = "<br/>".join(inteiro_teor_partes).strip() or None

        # =========================================================
        # 🔥 PROTEÇÃO DE TAMANHO (CRÍTICO)
        # =========================================================
        if inteiro_teor_montado and len(inteiro_teor_montado) > 10000:
            inteiro_teor_montado = inteiro_teor_montado[:10000] + "..."

        # =========================================================
        # 🔥 BUSCA DA MATRÍCULA
        # =========================================================
        matricula: Optional[Matricula] = (
            db.query(Matricula)
            .filter(
                Matricula.imovel_id == imovel.id,
                Matricula.numero_matricula == numero_matricula,
            )
            .first()
        )

        # =========================================================
        # CREATE
        # =========================================================
        if not matricula:
            try:
                matricula = Matricula(
                    imovel_id=imovel.id,
                    numero_matricula=numero_matricula,
                    livro=livro,
                    folha=folha,
                    comarca=comarca,
                    codigo_cartorio=codigo_cartorio,
                    cartorio_id=cartorio_id,
                    inteiro_teor=inteiro_teor_montado,
                    observacoes=observacoes,
                    status="ATIVA",
                )

                db.add(matricula)
                db.commit()
                db.refresh(matricula)

                print(f"✅ Matrícula criada: {numero_matricula}")
                return matricula

            except Exception as exc:
                OcrPipelineService._rollback_safely(db)
                print(f"❌ Erro ao criar matrícula: {str(exc)}")
                return None

        # =========================================================
        # UPDATE CONTROLADO
        # =========================================================
        alterou: bool = False

        if livro and livro != matricula.livro:
            matricula.livro = livro
            alterou = True

        if folha and folha != matricula.folha:
            matricula.folha = folha
            alterou = True

        if comarca and comarca != matricula.comarca:
            matricula.comarca = comarca
            alterou = True

        if codigo_cartorio and codigo_cartorio != matricula.codigo_cartorio:
            matricula.codigo_cartorio = codigo_cartorio
            alterou = True

        # 🔥 CARTÓRIO (APENAS SE NÃO EXISTIR)
        if not matricula.cartorio_id and cartorio_id:
            matricula.cartorio_id = cartorio_id
            alterou = True

        # =========================================================
        # 🔥 INTEIRO TEOR (REGRA MELHORADA)
        # =========================================================
        if inteiro_teor_montado:
            atual = matricula.inteiro_teor or ""

            if (
                not atual
                or len(inteiro_teor_montado) > len(atual)
                or inteiro_teor_montado != atual
            ):
                matricula.inteiro_teor = inteiro_teor_montado
                alterou = True

        # =========================================================
        # 🔥 OBSERVAÇÕES (CONTROLADO)
        # =========================================================
        if observacoes:
            atual_obs = matricula.observacoes or ""

            if not atual_obs or observacoes != atual_obs:
                matricula.observacoes = observacoes
                alterou = True

        # =========================================================
        # 🔥 COMMIT FINAL SE NECESSÁRIO
        # =========================================================
        if alterou:
            try:
                db.commit()
                db.refresh(matricula)
                print(f"ℹ️ Matrícula atualizada: {numero_matricula}")
            except Exception as exc:
                OcrPipelineService._rollback_safely(db)
                print(f"❌ Erro ao atualizar matrícula: {str(exc)}")
        else:
            print(f"ℹ️ Matrícula já existente (sem alterações): {numero_matricula}")

        return matricula
    
    @staticmethod
    def _resolver_geojson(dados: dict[str, Any]) -> Optional[str]:

        def _validar_geojson(geojson_str: str) -> Optional[str]:
            try:
                parsed = json.loads(geojson_str)

                if (
                    isinstance(parsed, dict)
                    and parsed.get("type") in ["Polygon", "MultiPolygon"]
                    and isinstance(parsed.get("coordinates"), list)
                ):
                    try:
                        from shapely.geometry import shape, mapping

                        geom = shape(parsed)

                        if not geom.is_valid:
                            geom = geom.buffer(0)

                        if geom.is_valid and not geom.is_empty:
                            # 🔥 RETORNA GEOMETRIA CORRIGIDA (CRÍTICO)
                            return json.dumps(mapping(geom))

                    except Exception as exc:
                        print(f"⚠️ Falha validação shapely: {str(exc)}")

            except Exception:
                pass

            return None

        # =========================================================
        # 🔥 PRIORIDADE: ESTRUTURA NORMALIZADA (OCR NORMALIZER)
        # =========================================================
        geometria = dados.get("geometria")

        if isinstance(geometria, dict):

            geojson = geometria.get("geojson")
            segmentos = geometria.get("segmentos")
            memorial_texto = geometria.get("memorial_texto")

            # ================= GEOJSON DIRETO =================
            geojson_normalizado = OcrPipelineService._normalizar_geojson(geojson)

            if geojson_normalizado:
                geo_validado = _validar_geojson(geojson_normalizado)
                if geo_validado:
                    print("✅ GeoJSON válido (estrutura normalizada + validado)")
                    return geo_validado

            # ================= SEGMENTOS =================
            if isinstance(segmentos, list) and segmentos:
                geojson_por_segmentos = OcrPipelineService._gerar_geojson_por_segmentos(
                    segmentos
                )

                if geojson_por_segmentos:
                    print("✅ GeoJSON gerado via segmentos (normalizado)")
                    return geojson_por_segmentos

            # ================= MEMORIAL =================
            if isinstance(memorial_texto, str) and memorial_texto.strip():
                geojson_por_memorial = OcrPipelineService._gerar_geojson_por_memorial(
                    memorial_texto
                )

                if geojson_por_memorial:
                    print("✅ GeoJSON gerado via memorial (normalizado)")
                    return geojson_por_memorial

        # =========================================================
        # 🔄 FALLBACK LEGADO
        # =========================================================
        geojson = dados.get("geojson")

        geojson_normalizado = OcrPipelineService._normalizar_geojson(geojson)

        if geojson_normalizado:
            geo_validado = _validar_geojson(geojson_normalizado)
            if geo_validado:
                print("⚠️ GeoJSON legado válido (corrigido)")
                return geo_validado

        # ================= SEGMENTOS LEGADO =================
        segmentos_memorial = dados.get("segmentos_memorial")

        if isinstance(segmentos_memorial, list) and segmentos_memorial:
            geojson_por_segmentos = OcrPipelineService._gerar_geojson_por_segmentos(
                segmentos_memorial
            )

            if geojson_por_segmentos:
                print("⚠️ GeoJSON gerado via segmentos (legado)")
                return geojson_por_segmentos

        # ================= MEMORIAL LEGADO =================
        memorial_texto = dados.get("memorial_texto")

        if isinstance(memorial_texto, str) and memorial_texto.strip():
            geojson_por_memorial = OcrPipelineService._gerar_geojson_por_memorial(
                memorial_texto
            )

            if geojson_por_memorial:
                print("⚠️ GeoJSON gerado via memorial (legado)")
                return geojson_por_memorial

        print("❌ Nenhuma fonte geométrica válida encontrada")
        return None
    
    @staticmethod
    def _normalizar_geojson(geojson: Any) -> Optional[str]:
        if geojson is None:
            return None

        parsed = None

        if isinstance(geojson, dict):
            parsed = geojson

        elif isinstance(geojson, str):
            texto = geojson.strip()

            if not texto:
                return None

            try:
                parsed = json.loads(texto)
            except Exception:
                print("⚠️ GeoJSON inválido recebido do OCR")
                return None

        if not isinstance(parsed, dict):
            return None

        # 🔥 VALIDAÇÃO ESTRUTURAL
        tipo = parsed.get("type")

        if tipo == "Feature":
            geometry = parsed.get("geometry")
            if not isinstance(geometry, dict):
                print("⚠️ GeoJSON ignorado: Feature sem geometry válido")
                return None
            parsed = geometry
            tipo = parsed.get("type")

        elif tipo == "FeatureCollection":
            features = parsed.get("features")
            if not isinstance(features, list) or not features:
                print("⚠️ GeoJSON ignorado: FeatureCollection sem features")
                return None

            geometria_feature = None
            for feature in features:
                if not isinstance(feature, dict):
                    continue

                geometry = feature.get("geometry")
                if (
                    isinstance(geometry, dict)
                    and geometry.get("type") in ["Polygon", "MultiPolygon"]
                    and isinstance(geometry.get("coordinates"), list)
                    and geometry.get("coordinates")
                ):
                    geometria_feature = geometry
                    break

            if not geometria_feature:
                print("⚠️ GeoJSON ignorado: FeatureCollection sem geometria poligonal")
                return None

            parsed = geometria_feature
            tipo = parsed.get("type")

        coords = parsed.get("coordinates")

        if tipo not in ["Polygon", "MultiPolygon"]:
            print("⚠️ GeoJSON ignorado: tipo inválido")
            return None

        if not isinstance(coords, list) or not coords:
            print("⚠️ GeoJSON ignorado: coordinates inválido")
            return None

        try:
            return json.dumps(parsed)
        except Exception:
            return None

    @staticmethod
    def _distancia_entre_pontos(
        p1: tuple[float, float],
        p2: tuple[float, float],
    ) -> float:
        dx: float = float(p2[0]) - float(p1[0])
        dy: float = float(p2[1]) - float(p1[1])
        return sqrt((dx * dx) + (dy * dy))

    @staticmethod
    def _fechar_anel(
        coords: list[tuple[float, float]]
    ) -> list[tuple[float, float]]:

        if len(coords) < 3:
            return coords

        # 🔥 EVITA MUTAÇÃO DO ORIGINAL
        coords_copy: list[tuple[float, float]] = list(coords)

        primeiro: tuple[float, float] = coords_copy[0]
        ultimo: tuple[float, float] = coords_copy[-1]

        distancia_fechamento: float = OcrPipelineService._distancia_entre_pontos(
            primeiro,
            ultimo,
        )

        # =========================================================
        # 🔥 FECHAMENTO POR TOLERÂNCIA (SIGEF SAFE)
        # =========================================================
        if distancia_fechamento <= OcrPipelineService.FECHAMENTO_TOLERANCIA_METROS:
            # 🔥 substitui último ponto pelo primeiro (padronização)
            coords_copy[-1] = primeiro
            return coords_copy

        # =========================================================
        # 🔥 FECHAMENTO FORÇADO (FLOAT SAFE)
        # =========================================================
        if distancia_fechamento > 0:
            coords_copy.append(primeiro)

        return coords_copy
    
    @staticmethod
    def _gerar_geojson_por_segmentos(
        segmentos_memorial: Any,
    ) -> Optional[str]:

        if not isinstance(segmentos_memorial, list) or not segmentos_memorial:
            return None

        coords: list[tuple[float, float]] = [(0.0, 0.0)]

        x: float = 0.0
        y: float = 0.0

        # =========================================================
        # 🔥 CONTROLE VETORIAL
        # =========================================================
        distancias_processadas: list[float] = []

        minx = 0.0
        miny = 0.0
        maxx = 0.0
        maxy = 0.0

        ultimo_azimute: Optional[float] = None

        # =========================================================
        # 🔥 LIMITES TÉCNICOS
        # =========================================================
        LIMITE_ABSOLUTO_SEGMENTO = 5000.0
        LIMITE_ENVELOPE = 50000.0
        LIMITE_SALTO_ANGULAR = 170.0

        for index, seg in enumerate(segmentos_memorial, start=1):

            if not isinstance(seg, dict):
                print(f"⚠️ Segmento inválido na posição {index}")
                return None

            angulo_raw = (
                seg.get("azimute")
                or seg.get("azimute_raw")
                or seg.get("rumo")
            )

            distancia_raw = seg.get("distancia")

            if angulo_raw is None or distancia_raw is None:
                print(f"⚠️ Segmento incompleto na posição {index}")
                return None

            try:

                azimute = OcrPipelineService._parse_angulo_para_graus(
                    str(angulo_raw)
                )

                if azimute < 0 or azimute > 360:
                    raise ValueError(
                        "Azimute fora do intervalo válido"
                    )

                distancia = OcrPipelineService._parse_distancia(
                    distancia_raw
                )

                if distancia <= 0:
                    raise ValueError(
                        "Distância inválida"
                    )

            except Exception as exc:

                print(
                    f"⚠️ Segmento inválido {index}: {str(exc)}"
                )

                return None

            # =====================================================
            # 🔥 CONTROLE DE SEGMENTO ABSURDO
            # =====================================================
            if distancia > LIMITE_ABSOLUTO_SEGMENTO:

                # =================================================
                # 🔥 TENTATIVA DE RECUPERAÇÃO OCR
                # =================================================
                #
                # CASO REAL:
                #
                # 299,51  -> OCR -> 29951
                # 105,22  -> OCR -> 10522
                #
                # NÃO podemos simplesmente aceitar valores gigantes,
                # mas também não podemos invalidar automaticamente.
                #
                # Estratégia:
                #
                # - tenta dividir por 100
                # - valida contexto vetorial
                # - valida explosão estatística
                #
                # =================================================
                distancia_corrigida = distancia / 100.0

                recuperado_por_ocr = False

                if (
                    distancia_corrigida > 0
                    and distancia_corrigida <= LIMITE_ABSOLUTO_SEGMENTO
                ):

                    if distancias_processadas:

                        media_distancias = (
                            sum(distancias_processadas)
                            / len(distancias_processadas)
                        )

                        if media_distancias > 0:

                            fator_corrigido = (
                                distancia_corrigida
                                / media_distancias
                            )

                            if fator_corrigido <= 25:

                                print(
                                    f"⚠️ Segmento {index} "
                                    f"corrigido automaticamente "
                                    f"via OCR decimal "
                                    f"({distancia:.2f}m -> "
                                    f"{distancia_corrigida:.2f}m)"
                                )

                                distancia = distancia_corrigida
                                recuperado_por_ocr = True

                    else:

                        print(
                            f"⚠️ Segmento {index} "
                            f"corrigido automaticamente "
                            f"via OCR decimal "
                            f"({distancia:.2f}m -> "
                            f"{distancia_corrigida:.2f}m)"
                        )

                        distancia = distancia_corrigida
                        recuperado_por_ocr = True

                if not recuperado_por_ocr:

                    print(
                        f"⚠️ Segmento {index} excede limite técnico: "
                        f"{distancia:.2f}m"
                    )

                    return None

            # =====================================================
            # 🔥 CONTROLE ESTATÍSTICO OCR
            # =====================================================
            if distancias_processadas:

                media_distancias = (
                    sum(distancias_processadas)
                    / len(distancias_processadas)
                )

                if media_distancias > 0:

                    fator_explosao = distancia / media_distancias

                    if fator_explosao > 25:

                        print(
                            f"⚠️ Segmento {index} com explosão vetorial "
                            f"(x{fator_explosao:.2f})"
                        )

                        return None

            distancias_processadas.append(distancia)

            # =====================================================
            # 🔥 CONTROLE ANGULAR
            # =====================================================
            if ultimo_azimute is not None:

                delta_angular = abs(
                    azimute - ultimo_azimute
                )

                delta_angular = min(
                    delta_angular,
                    360 - delta_angular,
                )

                if delta_angular > LIMITE_SALTO_ANGULAR:

                    print(
                        f"⚠️ Segmento {index} possui salto angular "
                        f"suspeito ({delta_angular:.2f}°)"
                    )

            ultimo_azimute = azimute

            azimute_rad = radians(azimute)

            dx: float = distancia * sin(azimute_rad)
            dy: float = distancia * cos(azimute_rad)

            # =====================================================
            # 🔥 PROTEÇÃO FLOAT
            # =====================================================
            if (
                math.isnan(dx)
                or math.isnan(dy)
                or math.isinf(dx)
                or math.isinf(dy)
            ):

                print(
                    f"⚠️ Segmento {index} gerou deslocamento inválido"
                )

                return None

            # =====================================================
            # 🔥 PROTEÇÃO CONTRA EXPLOSÃO
            # =====================================================
            if abs(dx) > 1e7 or abs(dy) > 1e7:

                print(
                    f"⚠️ Segmento {index} gerou deslocamento absurdo"
                )

                return None

            novo_x = x + dx
            novo_y = y + dy

            # =====================================================
            # 🔥 ENVELOPE ESPACIAL
            # =====================================================
            minx = min(minx, novo_x)
            miny = min(miny, novo_y)

            maxx = max(maxx, novo_x)
            maxy = max(maxy, novo_y)

            spanx = abs(maxx - minx)
            spany = abs(maxy - miny)

            if spanx > LIMITE_ENVELOPE or spany > LIMITE_ENVELOPE:

                print(
                    f"⚠️ Envelope geométrico inválido "
                    f"({spanx:.2f} x {spany:.2f})"
                )

                return None

            x = novo_x
            y = novo_y

            coords.append((x, y))

        if len(coords) < 4:

            print(
                "⚠️ Segmentos insuficientes para formar polígono"
            )

            return None

        # =========================================================
        # 🔥 ERRO DE FECHAMENTO
        # =========================================================
        erro_fechamento = (
            OcrPipelineService._distancia_entre_pontos(
                coords[0],
                coords[-1],
            )
        )

        limite_fechamento = (
            OcrPipelineService.FECHAMENTO_TOLERANCIA_METROS * 5
        )

        if erro_fechamento > limite_fechamento:

            print(
                f"⚠️ Erro de fechamento elevado: "
                f"{erro_fechamento:.2f}m"
            )

            return None

        coords = OcrPipelineService._fechar_anel(coords)

        # =========================================================
        # 🔥 VALIDAÇÃO DE DEGENERAÇÃO
        # =========================================================
        coords_unicos = [
            (
                round(p[0], 6),
                round(p[1], 6),
            )
            for p in coords
        ]

        if len(set(coords_unicos)) < 3:

            print(
                "⚠️ Coordenadas degeneradas "
                "(polígono inválido)"
            )

            return None

        polygon = Polygon(coords)

        # =========================================================
        # 🔥 NÃO ACEITA MULTIPOLYGON OCR
        # =========================================================
        if not polygon.is_valid:

            polygon_corrigido = polygon.buffer(0)

            if (
                polygon_corrigido.is_empty
                or not polygon_corrigido.is_valid
            ):

                print(
                    "⚠️ Polígono inválido mesmo após correção"
                )

                return None

            if polygon_corrigido.geom_type != "Polygon":

                print(
                    "⚠️ OCR gerou geometria fragmentada "
                    "(MultiPolygon bloqueado)"
                )

                return None

            polygon = polygon_corrigido

        if polygon.is_empty:

            print("⚠️ Polígono vazio")

            return None

        # =========================================================
        # 🔥 ÁREA DEGENERADA
        # =========================================================
        if polygon.area <= 0:

            print("⚠️ Área geométrica inválida")

            return None

        # =========================================================
        # 🔥 NORMALIZAÇÃO FINAL DO GEOJSON
        # =========================================================
        try:

            from shapely.geometry import mapping

            geojson_final = mapping(polygon)

            geojson_final["metadata"] = {
                "referencial": "LOCAL_CARTESIANO",
                "origem": "SEGMENTOS_MEMORIAL",
                "reconstruido_por_ocr": True,
                "possui_georreferenciamento_real": False,
                "tipo_geometria": "POLIGONO_RECONSTRUIDO",
                "engine": "OCR_PIPELINE",

                "fechamento_tolerancia_metros": (
                    OcrPipelineService
                    .FECHAMENTO_TOLERANCIA_METROS
                ),

                "erro_fechamento_metros": round(
                    float(erro_fechamento),
                    6,
                ),

                "vertices": len(coords) - 1,

                "bbox": {
                    "minx": round(minx, 6),
                    "miny": round(miny, 6),
                    "maxx": round(maxx, 6),
                    "maxy": round(maxy, 6),
                    "spanx": round(spanx, 6),
                    "spany": round(spany, 6),
                },

                "estatisticas_segmentos": {
                    "total_segmentos": len(distancias_processadas),

                    "distancia_min": round(
                        min(distancias_processadas),
                        6,
                    ),

                    "distancia_max": round(
                        max(distancias_processadas),
                        6,
                    ),

                    "distancia_media": round(
                        (
                            sum(distancias_processadas)
                            / len(distancias_processadas)
                        ),
                        6,
                    ),
                },
            }

            return json.dumps(
                geojson_final,
                ensure_ascii=False,
            )

        except Exception as exc:

            print(
                "⚠️ Falha ao converter polygon para GeoJSON: "
                f"{str(exc)}"
            )

            return None
        
    @staticmethod
    def _gerar_geojson_por_memorial(
        memorial_texto: Any,
    ) -> Optional[str]:

        if not isinstance(memorial_texto, str):
            return None

        texto = memorial_texto.strip()

        if not texto:
            return None

        try:

            resultado = MemorialParserService.gerar_geometria(
                texto
            )

        except Exception as exc:

            print(
                "⚠️ Falha ao gerar geometria "
                f"a partir do memorial: {str(exc)}"
            )

            return None

        geojson = resultado.get("geojson")

        # =========================================================
        # 🔥 VALIDAÇÃO ESTRUTURAL
        # =========================================================
        if (
            not isinstance(geojson, dict)
            or geojson.get("type") not in ["Polygon", "MultiPolygon"]
            or not isinstance(
                geojson.get("coordinates"),
                list,
            )
        ):
            return None

        try:

            from shapely.geometry import (
                mapping,
                shape,
            )

            geom = shape(geojson)

            # =====================================================
            # 🔥 GEOMETRIA VAZIA
            # =====================================================
            if geom.is_empty:

                print(
                    "⚠️ Geometria do memorial vazia"
                )

                return None

            # =====================================================
            # 🔥 CORREÇÃO TOPOLOGICA
            # =====================================================
            if not geom.is_valid:

                geom_corrigida = geom.buffer(0)

                if (
                    geom_corrigida.is_empty
                    or not geom_corrigida.is_valid
                ):

                    print(
                        "⚠️ Geometria do memorial "
                        "permaneceu inválida"
                    )

                    return None

                # =================================================
                # 🔥 BLOQUEIA MULTIPOLYGON
                # =================================================
                if geom_corrigida.geom_type != "Polygon":

                    print(
                        "⚠️ Memorial gerou geometria "
                        "fragmentada (MultiPolygon)"
                    )

                    return None

                geom = geom_corrigida

            # =====================================================
            # 🔥 SOMENTE POLYGON
            # =====================================================
            if geom.geom_type != "Polygon":

                print(
                    "⚠️ Memorial retornou geometria "
                    f"não suportada: {geom.geom_type}"
                )

                return None

            # =====================================================
            # 🔥 ÁREA DEGENERADA
            # =====================================================
            if geom.area <= 0:

                print(
                    "⚠️ Geometria do memorial "
                    "possui área inválida"
                )

                return None

            # =====================================================
            # 🔥 PADRONIZAÇÃO FINAL
            # =====================================================
            geojson_final = mapping(geom)

            # =====================================================
            # 🔥 METADATA TÉCNICA
            # =====================================================
            geojson_final["metadata"] = {
                "referencial": "LOCAL_CARTESIANO",
                "origem": "MEMORIAL_DESCRITIVO",
                "reconstruido_por_ocr": True,
                "possui_georreferenciamento_real": False,
                "tipo_geometria": "POLIGONO_RECONSTRUIDO",
                "engine": "OCR_PIPELINE",
                "geom_type": geom.geom_type,
                "vertices": len(
                    list(geom.exterior.coords)
                ) - 1,
                "area_modelo": round(
                    float(geom.area),
                    6,
                ),
            }

            return json.dumps(
                geojson_final,
                ensure_ascii=False,
            )

        except Exception as exc:

            print(
                "⚠️ Falha ao validar geometria "
                f"do memorial: {str(exc)}"
            )

            return None
        
    @staticmethod
    def _parse_angulo_para_graus(
        valor: str,
    ) -> float:

        valor_original = str(valor)

        valor_limpo = valor_original.strip().upper()

        # =========================================================
        # 🔥 NORMALIZAÇÃO OCR
        # =========================================================
        valor_limpo = valor_limpo.replace("º", "°")
        valor_limpo = valor_limpo.replace("’", "'")
        valor_limpo = valor_limpo.replace("`", "'")

        valor_limpo = valor_limpo.replace("“", '"')
        valor_limpo = valor_limpo.replace("”", '"')

        valor_limpo = valor_limpo.replace("O", "0")

        valor_limpo = " ".join(valor_limpo.split())

        # =========================================================
        # 🔥 RUMO QUADRANTAL
        # =========================================================
        #
        # Ex:
        # N 10°30'20" E
        # S 45°22' W
        #
        # =========================================================
        if re.match(
            r"^[NS]\s*.+\s*[EW]$",
            valor_limpo,
        ):

            az = MemorialParserService._rumo_para_azimute(
                valor_limpo
            )

            if az < 0 or az >= 360:
                raise ValueError(
                    "Rumo convertido inválido"
                )

            return az

        # =========================================================
        # 🔥 DIREÇÃO EMBUTIDA
        # =========================================================
        #
        # Ex:
        # 10°30' NE
        #
        # =========================================================
        match_direcao = re.search(
            r"(.+?)\s*([NS][EW])$",
            valor_limpo,
        )

        if match_direcao:

            angulo_base = (
                match_direcao.group(1).strip()
            )

            direcao = match_direcao.group(2)

            graus_base = (
                OcrPipelineService._parse_angulo_para_graus(
                    angulo_base
                )
            )

            if graus_base < 0 or graus_base > 90:
                raise ValueError(
                    "Ângulo base inválido "
                    "para rumo quadrantal"
                )

            if direcao == "NE":
                return graus_base

            elif direcao == "SE":
                return 180 - graus_base

            elif direcao == "SW":
                return 180 + graus_base

            elif direcao == "NW":
                return 360 - graus_base

        # =========================================================
        # 🔥 DMS COMPLETO
        # =========================================================
        #
        # Ex:
        # 01°22'35"
        #
        # =========================================================
        match_dms = re.search(
            r"(\d+)[°]\s*(\d+)?'?\s*(\d+(?:\.\d+)?)?\"?",
            valor_limpo,
        )

        if match_dms:

            graus, minutos, segundos = (
                match_dms.groups()
            )

            g = float(graus or 0)
            m = float(minutos or 0)
            s = float(segundos or 0)

            if m >= 60:
                raise ValueError(
                    "Minutos inválidos"
                )

            if s >= 60:
                raise ValueError(
                    "Segundos inválidos"
                )

            decimal = (
                g
                + (m / 60)
                + (s / 3600)
            )

            if decimal == 360:
                return 0.0

            if decimal < 0 or decimal > 360:
                raise ValueError(
                    "Ângulo DMS inválido"
                )

            return decimal

        # =========================================================
        # 🔥 OCR PARCIAL
        # =========================================================
        #
        # Ex:
        # 01 22 35
        #
        # =========================================================
        partes = re.findall(
            r"\d+(?:\.\d+)?",
            valor_limpo,
        )

        if len(partes) == 3:

            g, m, s = map(float, partes)

            if m >= 60:
                raise ValueError(
                    "Minutos inválidos"
                )

            if s >= 60:
                raise ValueError(
                    "Segundos inválidos"
                )

            decimal = (
                g
                + (m / 60)
                + (s / 3600)
            )

            if decimal == 360:
                return 0.0

            if decimal < 0 or decimal > 360:
                raise ValueError(
                    "Ângulo inválido OCR 3 partes"
                )

            return decimal

        if len(partes) == 2:

            g, m = map(float, partes)

            if m >= 60:
                raise ValueError(
                    "Minutos inválidos"
                )

            decimal = g + (m / 60)

            if decimal == 360:
                return 0.0

            if decimal < 0 or decimal > 360:
                raise ValueError(
                    "Ângulo inválido OCR 2 partes"
                )

            return decimal

        # =========================================================
        # 🔥 DECIMAL DIRETO
        # =========================================================
        try:

            decimal = float(
                valor_limpo.replace(",", ".")
            )

            if decimal == 360:
                return 0.0

            if decimal < 0 or decimal > 360:
                raise ValueError(
                    "Ângulo decimal inválido"
                )

            return decimal

        except Exception:
            pass

        # =========================================================
        # 🔥 OCR CORROMPIDO
        # =========================================================
        #
        # NÃO tenta mais "adivinhar"
        # removendo lixo arbitrariamente.
        #
        # Isso estava causando:
        # - explosão geométrica
        # - azimutes absurdos
        # - polígonos inválidos
        #
        # =========================================================
        raise ValueError(
            f"Ângulo inválido: {valor_original}"
        )
    
    @staticmethod
    def _parse_distancia(
        valor: Any,
    ) -> float:

        if valor is None:
            raise ValueError(
                "Distância ausente"
            )

        # =========================================================
        # NORMALIZAÇÃO BASE
        # =========================================================
        texto_original = str(valor)

        texto = texto_original.strip().upper()

        if not texto:
            raise ValueError(
                "Distância vazia"
            )

        # =========================================================
        # NORMALIZAÇÕES OCR
        # =========================================================
        texto = texto.replace("METROS", "")
        texto = texto.replace("METRO", "")
        texto = texto.replace("MTS", "")
        texto = texto.replace("MT", "")
        texto = texto.replace("M.", "")
        texto = texto.replace("M", "")

        # =========================================================
        # 🔥 OCR NUMÉRICO CONTROLADO
        # =========================================================
        #
        # Corrige:
        #
        # 1O5,22 -> 105,22
        # 15l.33 -> 151.33
        #
        # SEM corromper texto arbitrário
        #
        # =========================================================
        texto = re.sub(
            r"(?<=\d)[O](?=\d)",
            "0",
            texto,
        )

        texto = re.sub(
            r"(?<=\d)[LI](?=\d)",
            "1",
            texto,
        )

        texto = " ".join(
            texto.split()
        )

        # =========================================================
        # EXTRAÇÃO NUMÉRICA INTELIGENTE
        # =========================================================
        #
        # SUPORTA:
        #
        # 1.905,312
        # 1905,312
        # 1,905.312
        # 1905.312
        # 1905
        #
        # =========================================================
        match = re.search(
            (
                r"(-?\d{1,3}"
                r"(?:[.,]\d{3})*"
                r"(?:[.,]\d+)?"
                r"|-?\d+(?:[.,]\d+)?)"
            ),
            texto,
        )

        if not match:
            raise ValueError(
                f"Distância inválida: {valor}"
            )

        numero_str = (
            match.group(1).strip()
        )

        # =========================================================
        # NORMALIZAÇÃO PT-BR / EN-US
        # =========================================================
        virgulas = numero_str.count(",")
        pontos = numero_str.count(".")

        # =========================================================
        # FORMATO MISTO
        # =========================================================
        if virgulas > 0 and pontos > 0:

            ultima_virgula = (
                numero_str.rfind(",")
            )

            ultimo_ponto = (
                numero_str.rfind(".")
            )

            # PT-BR
            if ultima_virgula > ultimo_ponto:

                numero_str = (
                    numero_str.replace(".", "")
                )

                numero_str = (
                    numero_str.replace(",", ".")
                )

            # EN-US
            else:

                numero_str = (
                    numero_str.replace(",", "")
                )

        # =========================================================
        # SOMENTE VÍRGULA
        # =========================================================
        elif virgulas > 0 and pontos == 0:

            partes = numero_str.split(",")

            # decimal
            if len(partes[-1]) <= 3:

                numero_str = (
                    numero_str.replace(",", ".")
                )

            # milhar
            else:

                numero_str = (
                    numero_str.replace(",", "")
                )

        # =========================================================
        # SOMENTE PONTO
        # =========================================================
        elif pontos > 0 and virgulas == 0:

            partes = numero_str.split(".")

            # múltiplos pontos
            if len(partes) > 2:

                decimal = partes[-1]

                inteiro = "".join(
                    partes[:-1]
                )

                numero_str = (
                    f"{inteiro}.{decimal}"
                )

        # =========================================================
        # CONVERSÃO FINAL
        # =========================================================
        try:

            distancia = float(numero_str)

        except Exception as exc:

            raise ValueError(
                f"Falha ao converter distância: {valor}"
            ) from exc

        # =========================================================
        # VALIDAÇÕES TÉCNICAS
        # =========================================================
        if math.isnan(distancia):
            raise ValueError(
                "Distância NaN"
            )

        if math.isinf(distancia):
            raise ValueError(
                "Distância infinita"
            )

        if distancia <= 0:
            raise ValueError(
                "Distância <= 0"
            )

        # =========================================================
        # PROTEÇÃO OCR CORROMPIDO
        # =========================================================
        if distancia > 100000:

            raise ValueError(
                "Distância excessiva detectada: "
                f"{distancia}"
            )

        # =========================================================
        # PROTEÇÃO MICROSEGMENTOS
        # =========================================================
        if distancia < 0.5:

            raise ValueError(
                "Distância muito pequena/suspeita: "
                f"{distancia}"
            )

        return distancia
