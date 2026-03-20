from __future__ import annotations

import json
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

        result: dict[str, Any] = {
            "success": False,
            "document_id": document_id,
            "ocr_result_id": ocr_result_id,
            "pipeline": "MATRICULA",
            "steps": {
                "matricula": {},
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
                analise = MatriculaAnalysisService.analisar(
                    texto=matricula.inteiro_teor
                )
                result["steps"]["analise_juridica"] = analise
            else:
                result["steps"]["analise_juridica"] = {
                    "success": False,
                    "message": "Matrícula sem conteúdo suficiente para análise jurídica.",
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

        try:
            geojson = OcrPipelineService._resolver_geojson(dados)
        except Exception as exc:
            OcrPipelineService._rollback_safely(db)
            result["errors"].append(f"Resolver geojson: {str(exc)}")

        if geojson:
            try:
                analise_geo = GeometriaService.analisar_referencial(
                    geojson=geojson,
                    epsg_origem=4326,
                )

                tipo_referencial = str(analise_geo.get("tipo_referencial"))
                epsg_origem = 0 if tipo_referencial == "LOCAL_CARTESIANA" else 4326

                epsg_utm, area_ha, perimetro_m = GeometriaService.calcular_area_perimetro(
                    geojson=geojson,
                    epsg_origem=epsg_origem,
                )

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

                # ================= GEOJSON FILE =================
                geo_file = GeometriaService.exportar_geojson(
                    imovel_id=imovel.id,
                    geojson=geometria.geojson,
                )

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
                        },
                        gerado_em=datetime.utcnow(),
                    ),
                )

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
                }

                try:
                    from app.services.confrontante_service import ConfrontanteService

                    confrontantes = ConfrontanteService.processar_confrontantes(
                        db=db,
                        imovel=imovel,
                        geometria=geometria,
                        confrontantes_ocr=dados.get("confrontantes"),
                    )

                    result["steps"]["confrontantes"] = {
                        "success": True,
                        "total": len(confrontantes),
                    }

                except Exception as exc:
                    OcrPipelineService._rollback_safely(db)
                    result["steps"]["confrontantes"] = {
                        "success": False,
                        "message": f"Falha ao processar confrontantes: {str(exc)}",
                    }
                    result["errors"].append(f"Confrontantes: {str(exc)}")

            except Exception as exc:
                OcrPipelineService._rollback_safely(db)
                result["steps"]["geometria"] = {
                    "success": False,
                    "message": f"Falha ao gerar geometria: {str(exc)}",
                }
                result["errors"].append(f"Geometria: {str(exc)}")
        else:
            result["steps"]["geometria"] = {
                "success": False,
                "message": "Nenhuma fonte geométrica válida encontrada.",
            }

        # ================= MEMORIAL =================
        if geometria:
            try:
                memorial = MemorialService.gerar_memorial(
                    geometria_id=geometria.id,
                    geojson=geometria.geojson,
                    epsg_origem=geometria.epsg_origem,
                    area_hectares=geometria.area_hectares or 0,
                    perimetro_m=geometria.perimetro_m or 0,
                    imovel_id=imovel.id,
                )

                memorial_json = OcrPipelineService._json_safe(memorial)
                memorial_texto = str(memorial.get("texto_preview") or "").strip()

                if not memorial_texto:
                    raise ValueError("Memorial gerado sem texto_preview.")

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
                    "arquivo_url": memorial.get("arquivo_url"),
                    "tipo_referencial": memorial.get("tipo_referencial"),
                    "epsg_utm": memorial.get("epsg_utm"),
                    "message": "Memorial gerado com arquivo.",
                }

            except Exception as exc:
                OcrPipelineService._rollback_safely(db)
                result["steps"]["memorial"] = {
                    "success": False,
                    "message": f"Falha ao gerar memorial: {str(exc)}",
                }
                result["errors"].append(f"Memorial: {str(exc)}")
        else:
            result["steps"]["memorial"] = {
                "success": False,
                "skipped": True,
                "message": "Memorial não executado: geometria inexistente.",
            }

        # =========================================================
        # CROQUI
        # =========================================================
        if geometria:
            try:
                confrontantes = None
                try:
                    if isinstance(dados, dict):
                        confrontantes = dados.get("confrontantes")
                except Exception:
                    confrontantes = None

                svg = CroquiService.gerar_svg(
                    geometria.geojson,
                    confrontantes=confrontantes,
                )

                folder = f"app/uploads/imoveis/{imovel.id}/croqui"
                os.makedirs(folder, exist_ok=True)

                path_svg = f"{folder}/croqui_{geometria.id}.svg"

                with open(path_svg, "w", encoding="utf-8") as f:
                    f.write(svg)

                url_svg = OcrPipelineService._build_file_url(base_url, path_svg)

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
                            "confrontantes_incluidos": bool(confrontantes),
                        },
                        gerado_em=datetime.utcnow(),
                    ),
                )

                result["steps"]["croqui"] = {
                    "success": True,
                    "arquivo_path": path_svg,
                    "arquivo_url": url_svg,
                    "documento_tecnico_id": doc_croqui.id,
                    "confrontantes_incluidos": bool(confrontantes),
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
                        },
                        gerado_em=datetime.utcnow(),
                    ),
                )

                result["steps"]["cad"] = {
                    "success": True,
                    "arquivo_path": path_scr,
                    "arquivo_url": url_scr,
                    "documento_tecnico_id": doc_cad.id,
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
            }

        # =========================================================
        # TXT (LISP / COORDENADAS)
        # =========================================================
        if geometria:
            try:
                from app.services.txt_lisp_service import TxtLispService

                txt = TxtLispService.gerar_txt(geometria.geojson)

                path_txt = TxtLispService.salvar_txt(
                    imovel_id=imovel.id,
                    txt=txt,
                )

                url_txt = OcrPipelineService._build_file_url(base_url, path_txt)

                doc_txt = create_documento_tecnico(
                    db=db,
                    imovel_id=imovel.id,
                    data=DocumentoTecnicoCreate(
                        document_group_key="COORDENADAS_TXT",
                        tipo="TXT Coordenadas",
                        status_tecnico="EM_ANALISE",
                        arquivo_path=path_txt,
                        metadata_json={
                            "geometria_id": geometria.id,
                            "formato": "TXT",
                        },
                        gerado_em=datetime.utcnow(),
                    ),
                )

                result["steps"]["txt"] = {
                    "success": True,
                    "arquivo_path": path_txt,
                    "arquivo_url": url_txt,
                    "documento_tecnico_id": doc_txt.id,
                    "message": f"TXT gerado: {path_txt}",
                }

                print(f"✅ TXT gerado: {path_txt}")

            except Exception as exc:
                OcrPipelineService._rollback_safely(db)
                result["steps"]["txt"] = {
                    "success": False,
                    "message": f"Falha ao gerar TXT: {str(exc)}",
                }
                result["errors"].append(f"TXT: {str(exc)}")
                print(f"❌ Falha ao gerar TXT: {str(exc)}")
        else:
            result["steps"]["txt"] = {
                "success": False,
                "skipped": True,
                "message": "TXT não executado: geometria inexistente.",
            }

        # =========================================================
        # DXF
        # =========================================================
        if geometria:
            try:
                from app.services.dxf_export_service import DxfExportService

                doc_dxf_file = DxfExportService.gerar_dxf(geometria.geojson)

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
                        },
                        gerado_em=datetime.utcnow(),
                    ),
                )

                result["steps"]["dxf"] = {
                    "success": True,
                    "arquivo_path": path_dxf,
                    "arquivo_url": url_dxf,
                    "documento_tecnico_id": doc_dxf.id,
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
            }

        # =========================================================
        # SHP (QGIS READY + VALIDAÇÃO TOPOLOGICA)
        # =========================================================
        if geometria:
            try:
                from app.services.shp_export_service import ShpExportService
                import os

                gdf = ShpExportService.gerar_shp(geometria.geojson)

                path_folder = ShpExportService.salvar_shp(
                    imovel_id=imovel.id,
                    gdf=gdf,
                )

                # 🔥 localizar arquivo .shp real dentro da pasta
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

                    path_sigef = sigef_data.get("arquivo_path")
                    documento_tecnico_id = sigef_data.get("documento_tecnico_id")
                    url_sigef = OcrPipelineService._build_file_url(base_url, path_sigef)

                    if not documento_tecnico_id and path_sigef:
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
                        "message": "Planilha SIGEF gerada com sucesso.",
                    }

                    print("✅ Planilha SIGEF gerada")

                except Exception as exc:
                    OcrPipelineService._rollback_safely(db)
                    result["steps"]["sigef_csv"] = {
                        "success": False,
                        "message": f"Falha ao gerar SIGEF CSV: {str(exc)}",
                    }
                    result["errors"].append(f"SIGEF CSV: {str(exc)}")
                    print(f"❌ Falha ao gerar SIGEF CSV: {str(exc)}")
            else:
                result["steps"]["sigef_csv"] = {
                    "success": False,
                    "skipped": True,
                    "message": (
                        "SIGEF CSV não executado: geometria local/cartesiana "
                        "não é exportável como SIGEF oficial."
                    ),
                }

                print("ℹ️ SIGEF CSV ignorado: geometria local/cartesiana")
        else:
            result["steps"]["sigef_csv"] = {
                "success": False,
                "skipped": True,
                "message": "SIGEF CSV não executado: geometria inexistente.",
            }

        # =========================================================
        # SUCESSO FINAL
        # =========================================================
        geometria_ok = bool(result["steps"]["geometria"].get("success"))
        memorial_ok = bool(result["steps"]["memorial"].get("success"))
        croqui_ok = bool(result["steps"]["croqui"].get("success"))
        cad_ok = bool(result["steps"]["cad"].get("success"))

        epsg_origem_atual = geometria.epsg_origem if geometria else None

        if geometria and epsg_origem_atual and epsg_origem_atual > 0:
            sigef_ok = bool(result["steps"]["sigef_csv"].get("success"))
            result["success"] = (
                geometria_ok and memorial_ok and croqui_ok and cad_ok and sigef_ok
            )
        else:
            result["success"] = geometria_ok and memorial_ok and croqui_ok and cad_ok

        print("🏁 Pipeline OCR concluído")
        return result

    @staticmethod
    def _upsert_matricula(
        db: Session,
        imovel: Imovel,
        dados: dict[str, Any],
    ) -> Optional[Matricula]:
        numero_matricula: Optional[str] = None

        if isinstance(dados.get("matricula"), dict):
            numero_matricula = dados["matricula"].get("numero")

        if not numero_matricula:
            numero_matricula = dados.get("numero_matricula") or dados.get("matricula")

        if numero_matricula is not None:
            numero_matricula = str(numero_matricula).strip()

        if not numero_matricula:
            return None

        matricula: Optional[Matricula] = (
            db.query(Matricula)
            .filter(
                Matricula.imovel_id == imovel.id,
                Matricula.numero_matricula == numero_matricula,
            )
            .first()
        )

        descricao_imovel: Optional[str] = (
            dados.get("descricao_imovel")
            or (
                dados.get("imovel", {}).get("descricao")
                if isinstance(dados.get("imovel"), dict)
                else None
            )
        )

        comarca: Optional[str] = (
            dados.get("comarca")
            or (
                dados.get("matricula", {}).get("comarca")
                if isinstance(dados.get("matricula"), dict)
                else None
            )
        )

        if descricao_imovel is not None:
            descricao_imovel = str(descricao_imovel).strip()

        if comarca is not None:
            comarca = str(comarca).strip()

        if not matricula:
            matricula = Matricula(
                imovel_id=imovel.id,
                numero_matricula=numero_matricula,
                comarca=comarca,
                inteiro_teor=descricao_imovel,
            )

            db.add(matricula)
            db.commit()
            db.refresh(matricula)

            print(f"✅ Matrícula criada: {numero_matricula}")
            return matricula

        alterou: bool = False

        if comarca and not matricula.comarca:
            matricula.comarca = comarca
            alterou = True

        if descricao_imovel and not matricula.inteiro_teor:
            matricula.inteiro_teor = descricao_imovel
            alterou = True

        if alterou:
            db.commit()
            db.refresh(matricula)
            print(f"ℹ️ Matrícula atualizada: {numero_matricula}")
        else:
            print(f"ℹ️ Matrícula já existente (sem alterações): {numero_matricula}")

        return matricula

    @staticmethod
    def _resolver_geojson(dados: dict[str, Any]) -> Optional[str]:
        geojson = dados.get("geojson")

        geojson_normalizado = OcrPipelineService._normalizar_geojson(geojson)

        if geojson_normalizado:
            try:
                parsed = json.loads(geojson_normalizado)

                if (
                    isinstance(parsed, dict)
                    and parsed.get("type") in ["Polygon", "MultiPolygon"]
                    and isinstance(parsed.get("coordinates"), list)
                ):
                    print("✅ GeoJSON válido recebido diretamente do OCR")
                    return geojson_normalizado
                else:
                    print("⚠️ GeoJSON do OCR ignorado (estrutura inválida)")

            except Exception:
                print("⚠️ GeoJSON do OCR inválido (json malformado)")

        segmentos_memorial = None

        if isinstance(dados.get("geometria"), dict):
            segmentos_memorial = dados["geometria"].get("segmentos")

        if not segmentos_memorial:
            segmentos_memorial = dados.get("segmentos_memorial")

        if isinstance(segmentos_memorial, list) and segmentos_memorial:
            geojson_por_segmentos = OcrPipelineService._gerar_geojson_por_segmentos(
                segmentos_memorial
            )

            if geojson_por_segmentos:
                print("✅ GeoJSON gerado a partir de segmentos")
                return geojson_por_segmentos

        memorial_texto = None

        if isinstance(dados.get("geometria"), dict):
            memorial_texto = dados["geometria"].get("memorial_texto")

        if not memorial_texto:
            memorial_texto = dados.get("memorial_texto")

        geojson_por_memorial = OcrPipelineService._gerar_geojson_por_memorial(
            memorial_texto
        )

        if geojson_por_memorial:
            print("✅ GeoJSON gerado a partir de memorial_texto")
            return geojson_por_memorial

        print("❌ Nenhuma fonte geométrica válida encontrada")
        return None

    @staticmethod
    def _normalizar_geojson(geojson: Any) -> Optional[str]:
        if geojson is None:
            return None

        if isinstance(geojson, dict):
            try:
                return json.dumps(geojson)
            except Exception:
                return None

        if isinstance(geojson, str):
            texto = geojson.strip()

            if not texto:
                return None

            try:
                json.loads(texto)
                return texto
            except Exception:
                print("⚠️ GeoJSON inválido recebido do OCR")
                return None

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
    def _fechar_anel(coords: list[tuple[float, float]]) -> list[tuple[float, float]]:
        if len(coords) < 3:
            return coords

        primeiro: tuple[float, float] = coords[0]
        ultimo: tuple[float, float] = coords[-1]

        distancia_fechamento = OcrPipelineService._distancia_entre_pontos(
            primeiro,
            ultimo,
        )

        if distancia_fechamento <= OcrPipelineService.FECHAMENTO_TOLERANCIA_METROS:
            return coords[:-1] + [primeiro]

        if primeiro != ultimo:
            coords.append(primeiro)

        return coords

    @staticmethod
    def _gerar_geojson_por_segmentos(
        segmentos_memorial: Any,
    ) -> Optional[str]:
        if not isinstance(segmentos_memorial, list) or not segmentos_memorial:
            return None

        coords: list[tuple[float, float]] = [(0.0, 0.0)]
        x = 0.0
        y = 0.0

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
                azimute = OcrPipelineService._parse_angulo_para_graus(str(angulo_raw))

                if azimute < 0 or azimute > 360:
                    raise ValueError("Azimute fora do intervalo válido")

                distancia = OcrPipelineService._parse_distancia(distancia_raw)

                if distancia <= 0:
                    raise ValueError("Distância inválida")

            except Exception as exc:
                print(f"⚠️ Segmento inválido {index}: {str(exc)}")
                return None

            azimute_rad = radians(azimute)

            dx = distancia * sin(azimute_rad)
            dy = distancia * cos(azimute_rad)

            x += dx
            y += dy

            coords.append((x, y))

        if len(coords) < 4:
            print("⚠️ Segmentos insuficientes para formar polígono")
            return None

        coords = OcrPipelineService._fechar_anel(coords)

        if len(set(coords)) < 3:
            print("⚠️ Coordenadas degeneradas (polígono inválido)")
            return None

        polygon = Polygon(coords)

        if not polygon.is_valid:
            polygon = polygon.buffer(0)

        if polygon.is_empty or not polygon.is_valid:
            print("⚠️ Polígono inválido mesmo após correção")
            return None

        return json.dumps(polygon.__geo_interface__)

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
            resultado = MemorialParserService.gerar_geometria(texto)
        except Exception as exc:
            print(f"⚠️ Falha ao gerar geometria a partir do memorial: {str(exc)}")
            return None

        geojson = resultado.get("geojson")

        if not isinstance(geojson, dict):
            return None

        try:
            return json.dumps(geojson)
        except Exception:
            return None

    @staticmethod
    def _parse_distancia(valor: Any) -> float:
        if isinstance(valor, (int, float)):
            return float(valor)

        texto = str(valor).strip()

        if not texto:
            raise ValueError("Distância vazia")

        texto = texto.replace(".", "").replace(",", ".")

        try:
            distancia = float(texto)
        except Exception:
            raise ValueError(f"Distância inválida: {valor}")

        if distancia <= 0:
            raise ValueError("Distância deve ser positiva")

        return distancia

    @staticmethod
    def _parse_angulo_para_graus(valor: str) -> float:
        valor_limpo = " ".join(valor.strip().upper().split())

        if re.match(r"^[NS]\s*.+\s*[EW]$", valor_limpo):
            return MemorialParserService._rumo_para_azimute(valor_limpo)

        match_dms = re.search(
            r"(\d+)[°º]\s*(\d+)'?\s*(\d+(?:\.\d+)?)?\"?",
            valor_limpo,
        )

        if match_dms:
            graus, minutos, segundos = match_dms.groups()

            g = float(graus)
            m = float(minutos)
            s = float(segundos or 0)

            decimal = g + (m / 60) + (s / 3600)

            if decimal < 0 or decimal > 360:
                raise ValueError("Ângulo DMS inválido")

            return decimal

        try:
            decimal = float(valor_limpo.replace(",", "."))
            if decimal < 0 or decimal > 360:
                raise ValueError("Ângulo fora do intervalo")
            return decimal
        except Exception:
            raise ValueError(f"Ângulo inválido: {valor}")