from __future__ import annotations

import json
import math
import os
import re
import logging
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
from app.services.matricula_pdf_service import MatriculaPdfService
from app.services.matricula_ocr_processor_service import MatriculaOcrProcessorService

logger = logging.getLogger(__name__)


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
    def _salvar_arquivo_pipeline_ocr(
        imovel_id: int,
        pipeline: str,
        nome_base: str,
        extensao: str,
        conteudo: str,
    ) -> dict[str, str]:

        if not imovel_id:
            raise ValueError("imovel_id inválido para salvar arquivo OCR.")

        if not conteudo:
            raise ValueError("Conteúdo vazio para salvar arquivo OCR.")

        pipeline_slug = (
            str(pipeline or "ocr")
            .strip()
            .lower()
            .replace(" ", "_")
        )

        nome_slug = (
            str(nome_base or "documento")
            .strip()
            .lower()
            .replace(" ", "_")
        )

        extensao_limpa = (
            str(extensao or "txt")
            .strip()
            .lower()
            .lstrip(".")
        )

        ts = int(datetime.utcnow().timestamp())

        folder = (
            f"app/uploads/imoveis/"
            f"{imovel_id}/ocr/{pipeline_slug}"
        )

        os.makedirs(folder, exist_ok=True)

        filename = f"{nome_slug}_{ts}.{extensao_limpa}"

        path = f"{folder}/{filename}"

        with open(path, "w", encoding="utf-8") as arquivo:
            arquivo.write(conteudo)

        return {
            "arquivo_path": path,
            "arquivo_url": OcrPipelineService._build_file_url(
                "https://geoincra.escriturafacil.com",
                path,
            ),
        }

    @staticmethod
    def _formatar_json_legivel(
        dados: object,
    ) -> str:

        return json.dumps(
            OcrPipelineService._json_safe(dados),
            ensure_ascii=False,
            indent=2,
        )

    @staticmethod
    def executar_pipeline(
        db: Session,
        document_id: int,
        ocr_result_id: int | None,
        prompt_categoria: str,
        dados_extraidos: dict[str, object],
    ) -> dict[str, object]:
        result: dict[str, object] = {
            "success": False,
            "document_id": document_id,
            "ocr_result_id": ocr_result_id,
            "categoria": prompt_categoria,
            "pipeline": None,
            "steps": {},
            "errors": [],
        }

        if not prompt_categoria:
            result["errors"].append("Categoria de prompt ausente.")
            return result

        categoria = OcrPipelineService._normalizar_categoria(prompt_categoria)
        pipeline = OcrPipelineService._resolver_pipeline_por_categoria(categoria)

        if not pipeline:
            result["errors"].append(
                f"Pipeline sem tratamento para categoria: {prompt_categoria}"
            )
            return result

        if pipeline == "MATRICULA_COMPLETA":
            dados_normalizados = normalizar_dados_ocr(dados_extraidos)

            try:
                OCRStructured(**dados_normalizados)
            except Exception as exc:
                return {
                    "success": False,
                    "document_id": document_id,
                    "ocr_result_id": ocr_result_id,
                    "categoria": prompt_categoria,
                    "pipeline": pipeline,
                    "steps": {},
                    "errors": [f"OCR inválido estruturalmente: {str(exc)}"],
                }

            return OcrPipelineService._pipeline_matricula(
                db=db,
                document_id=document_id,
                ocr_result_id=ocr_result_id,
                dados=dados_normalizados,
            )

        if pipeline == "DADOS_BRUTOS_COMPLETO":
            return OcrPipelineService._pipeline_dados_brutos(
                db=db,
                document_id=document_id,
                ocr_result_id=ocr_result_id,
                prompt_categoria=prompt_categoria,
                dados=dados_extraidos,
            )

        if pipeline == "DOCUMENTOS_PESSOAIS":
            return OcrPipelineService._pipeline_documentos_pessoais(
                db=db,
                document_id=document_id,
                ocr_result_id=ocr_result_id,
                prompt_categoria=prompt_categoria,
                dados=dados_extraidos,
            )

        if pipeline == "FICHA_CADASTRAL_SIG":
            return OcrPipelineService._pipeline_ficha_cadastral_sig(
                db=db,
                document_id=document_id,
                ocr_result_id=ocr_result_id,
                prompt_categoria=prompt_categoria,
                dados=dados_extraidos,
            )

        if pipeline == "CONFRONTANTES_CROQUI":
            return OcrPipelineService._pipeline_confrontantes_croqui(
                db=db,
                document_id=document_id,
                ocr_result_id=ocr_result_id,
                prompt_categoria=prompt_categoria,
                dados=dados_extraidos,
            )

        result["errors"].append(
            f"Pipeline resolvido, mas sem executor interno: {pipeline}"
        )
        return result

    @staticmethod
    def _normalizar_categoria(texto: str) -> str:
        mapa = str.maketrans(
            "áàãâäéèêëíìîïóòõôöúùûüçÁÀÃÂÄÉÈÊËÍÌÎÏÓÒÕÔÖÚÙÛÜÇ",
            "aaaaaeeeeiiiiooooouuuucAAAAAEEEEIIIIOOOOOUUUUC",
        )

        texto_normalizado = str(texto or "").strip().translate(mapa).lower()
        texto_normalizado = re.sub(r"[^a-z0-9]+", "_", texto_normalizado)
        texto_normalizado = re.sub(r"_+", "_", texto_normalizado).strip("_")

        return texto_normalizado

    @staticmethod
    def _resolver_pipeline_por_categoria(categoria: str) -> str | None:
        categorias_matricula = {
            "matricula_imovel",
            "analise_matricula",
            "analise_matricula_completa",
            "analise_de_matricula_de_imovel",
            "analise_tecnica_completa_de_matricula",
        }

        categorias_dados_brutos = {
            "dados_brutos",
            "dados_brutos_completo",
            "dados_brutos_de_documentos",
            "dados_brutos_do_documento",
            "extracao_dados_brutos",
            "extracao_bruta",
        }

        categorias_documentos_pessoais = {
            "documento_pessoal",
            "documentos_pessoais",
            "extracao_documentos_pessoais",
            "extracao_de_documentos_pessoais",
            "rg_cpf_cnh",
        }

        categorias_sig = {
            "ficha_cadastral_sig",
            "ficha_cadastral_de_imovel_sig",
            "ficha_cadastral_imovel_sig",
            "sig",
            "cadastro_sig",
            "cadastro_imovel_sig",
        }

        categorias_confrontantes_croqui = {
            "confrontantes_croqui",
            "insercao_confrontantes_croqui",
            "insercao_de_confrontantes_no_croqui",
            "inserir_confrontantes_no_croqui",
            "croqui_confrontantes",
        }

        if categoria in categorias_matricula:
            return "MATRICULA_COMPLETA"

        if categoria in categorias_dados_brutos:
            return "DADOS_BRUTOS_COMPLETO"

        if categoria in categorias_documentos_pessoais:
            return "DOCUMENTOS_PESSOAIS"

        if categoria in categorias_sig:
            return "FICHA_CADASTRAL_SIG"

        if categoria in categorias_confrontantes_croqui:
            return "CONFRONTANTES_CROQUI"

        return None
    
    @staticmethod
    def _pipeline_dados_brutos(
        db: Session,
        document_id: int,
        ocr_result_id: int | None,
        prompt_categoria: str,
        dados: dict[str, object],
    ) -> dict[str, object]:

        result: dict[str, object] = {
            "success": False,
            "document_id": document_id,
            "ocr_result_id": ocr_result_id,
            "pipeline": "DADOS_BRUTOS_COMPLETO",
            "categoria": prompt_categoria,
            "steps": {},
            "errors": [],
            "warnings": [],
        }

        try:

            doc = (
                db.query(Document)
                .filter(Document.id == document_id)
                .first()
            )

            if not doc:
                raise Exception(
                    "Documento não encontrado."
                )

            imovel = (
                db.query(Imovel)
                .filter(Imovel.project_id == doc.project_id)
                .first()
            )

            if not imovel:
                raise Exception(
                    "Projeto não possui imóvel vinculado."
                )

            # =====================================================
            # 🔥 PAYLOAD NORMALIZADO
            # =====================================================
            payload_json = OcrPipelineService._json_safe(
                dados
            )

            total_campos = (
                len(payload_json)
                if isinstance(payload_json, dict)
                else 0
            )

            # =====================================================
            # 🔥 QUALIDADE OCR
            # =====================================================
            qualidade_ocr = (
                dados.get("qualidade")
                if isinstance(dados, dict)
                else None
            )

            score_ocr = 0

            confianca_geral = None

            if isinstance(qualidade_ocr, dict):

                try:
                    score_ocr = int(
                        float(
                            qualidade_ocr.get("score")
                            or qualidade_ocr.get("confidence")
                            or 0
                        )
                    )
                except Exception:
                    score_ocr = 0

                confianca_geral = (
                    qualidade_ocr.get("confianca_geral")
                    or qualidade_ocr.get("confidence")
                )

            score_ocr = max(
                0,
                min(
                    100,
                    score_ocr,
                ),
            )

            # =====================================================
            # 🔥 GERAÇÃO DE ARQUIVOS FÍSICOS
            # =====================================================
            json_legivel = (
                OcrPipelineService._formatar_json_legivel(
                    payload_json
                )
            )

            txt_legivel = (
                "RELATÓRIO OCR - DADOS BRUTOS\n"
                "\n"
                f"DOCUMENT ID: {document_id}\n"
                f"OCR RESULT ID: {ocr_result_id}\n"
                f"CATEGORIA: {prompt_categoria}\n"
                f"TOTAL CAMPOS: {total_campos}\n"
                f"SCORE OCR: {score_ocr}\n"
                "\n"
                "====================================================\n"
                "JSON EXTRAÍDO\n"
                "====================================================\n"
                "\n"
                f"{json_legivel}"
            )

            arquivo_json = (
                OcrPipelineService._salvar_arquivo_pipeline_ocr(
                    imovel_id=imovel.id,
                    pipeline="dados_brutos",
                    nome_base="dados_brutos",
                    extensao="json",
                    conteudo=json_legivel,
                )
            )

            arquivo_txt = (
                OcrPipelineService._salvar_arquivo_pipeline_ocr(
                    imovel_id=imovel.id,
                    pipeline="dados_brutos",
                    nome_base="dados_brutos_relatorio",
                    extensao="txt",
                    conteudo=txt_legivel,
                )
            )

            # =====================================================
            # 🔥 DOCUMENTO TÉCNICO
            # =====================================================
            documento_tecnico = create_documento_tecnico(
                db=db,
                imovel_id=imovel.id,
                data=DocumentoTecnicoCreate(
                    document_group_key="OCR_DADOS_BRUTOS",

                    tipo="OCR Dados Brutos",

                    status_tecnico="EM_ANALISE",

                    conteudo_texto=txt_legivel,

                    conteudo_json=payload_json,

                    arquivo_path=arquivo_json.get(
                        "arquivo_path"
                    ),

                    metadata_json={
                        "ocr_result_id": ocr_result_id,
                        "document_id": document_id,
                        "categoria": prompt_categoria,

                        "pipeline": (
                            "DADOS_BRUTOS_COMPLETO"
                        ),

                        "pipeline_version": 2,

                        "total_campos_extraidos": (
                            total_campos
                        ),

                        "qualidade_score": score_ocr,

                        "confianca_geral": (
                            confianca_geral
                        ),

                        "arquivos_gerados": {
                            "json": arquivo_json,
                            "txt": arquivo_txt,
                        },
                    },

                    gerado_em=datetime.utcnow(),
                ),
            )

            # =====================================================
            # 🔥 RESULTADO PRINCIPAL
            # =====================================================
            result["success"] = True

            result["steps"] = {
                "dados_brutos": {
                    "success": True,

                    "documento_tecnico_id": (
                        documento_tecnico.id
                    ),

                    "document_group_key": (
                        "OCR_DADOS_BRUTOS"
                    ),

                    "tipo_documento": (
                        "OCR Dados Brutos"
                    ),

                    "pipeline": (
                        "DADOS_BRUTOS_COMPLETO"
                    ),

                    "pipeline_version": 2,

                    "categoria_prompt": (
                        prompt_categoria
                    ),

                    "ocr_result_id": (
                        ocr_result_id
                    ),

                    "document_id": (
                        document_id
                    ),

                    "imovel_id": (
                        imovel.id
                    ),

                    "total_campos": (
                        total_campos
                    ),

                    "qualidade_score": (
                        score_ocr
                    ),

                    "confianca_geral": (
                        confianca_geral
                    ),

                    "payload": (
                        payload_json
                    ),

                    "arquivo_json_path": (
                        arquivo_json.get(
                            "arquivo_path"
                        )
                    ),

                    "arquivo_json_url": (
                        arquivo_json.get(
                            "arquivo_url"
                        )
                    ),

                    "arquivo_txt_path": (
                        arquivo_txt.get(
                            "arquivo_path"
                        )
                    ),

                    "arquivo_txt_url": (
                        arquivo_txt.get(
                            "arquivo_url"
                        )
                    ),

                    "arquivos_gerados": {
                        "json": arquivo_json,
                        "txt": arquivo_txt,
                    },

                    "message": (
                        "Dados brutos processados "
                        "com geração completa "
                        "de arquivos físicos."
                    ),
                },
            }

            # =====================================================
            # 🔥 METADATA PIPELINE
            # =====================================================
            result["metadata_pipeline"] = {
                "pipeline": (
                    "DADOS_BRUTOS_COMPLETO"
                ),

                "pipeline_version": 2,

                "engine_origem": (
                    "OCR_PIPELINE"
                ),

                "normalizador": (
                    "normalizar_dados_ocr"
                ),

                "categoria_prompt": (
                    prompt_categoria
                ),

                "document_group_key": (
                    "OCR_DADOS_BRUTOS"
                ),

                "ocr_result_id": (
                    ocr_result_id
                ),

                "document_id": (
                    document_id
                ),

                "imovel_id": (
                    imovel.id
                ),

                "documento_tecnico_id": (
                    documento_tecnico.id
                ),

                "tipo_documento": (
                    "OCR Dados Brutos"
                ),

                "arquivos_gerados": {
                    "json": {
                        "path": arquivo_json.get(
                            "arquivo_path"
                        ),
                        "url": arquivo_json.get(
                            "arquivo_url"
                        ),
                    },

                    "txt": {
                        "path": arquivo_txt.get(
                            "arquivo_path"
                        ),
                        "url": arquivo_txt.get(
                            "arquivo_url"
                        ),
                    },
                },
            }

            # =====================================================
            # 🔥 ESTATÍSTICAS
            # =====================================================
            result["estatisticas"] = {
                "total_campos_extraidos": (
                    total_campos
                ),

                "score_ocr": (
                    score_ocr
                ),

                "confianca_geral": (
                    confianca_geral
                ),

                "arquivos_gerados": 2,

                "possui_json": bool(
                    arquivo_json.get(
                        "arquivo_path"
                    )
                ),

                "possui_txt": bool(
                    arquivo_txt.get(
                        "arquivo_path"
                    )
                ),

                "pipeline_processado": True,
            }

            # =====================================================
            # 🔥 VALIDAÇÃO PIPELINE
            # =====================================================
            result["validacao_pipeline"] = {
                "pipeline": (
                    "DADOS_BRUTOS_COMPLETO"
                ),

                "pipeline_version": 2,

                "document_id": (
                    document_id
                ),

                "ocr_result_id": (
                    ocr_result_id
                ),

                "imovel_id": (
                    imovel.id
                ),

                "documento_tecnico_id": (
                    documento_tecnico.id
                ),

                "persistencia_ok": True,

                "payload_ok": bool(
                    payload_json
                ),

                "payload_tipo": (
                    type(payload_json).__name__
                ),

                "qualidade_score": (
                    score_ocr
                ),

                "qualidade_minima_ok": (
                    score_ocr >= 60
                ),

                "confianca_geral": (
                    confianca_geral
                ),

                "arquivo_json_gerado": bool(
                    arquivo_json.get(
                        "arquivo_path"
                    )
                ),

                "arquivo_txt_gerado": bool(
                    arquivo_txt.get(
                        "arquivo_path"
                    )
                ),

                "arquivo_json_path": (
                    arquivo_json.get(
                        "arquivo_path"
                    )
                ),

                "arquivo_txt_path": (
                    arquivo_txt.get(
                        "arquivo_path"
                    )
                ),

                "pipeline_processado": True,
            }

            return result

        except Exception as exc:

            OcrPipelineService._rollback_safely(db)

            error_message = str(exc)

            result["success"] = False

            result["errors"].append(
                error_message
            )

            result["steps"] = {
                "dados_brutos": {
                    "success": False,

                    "pipeline": (
                        "DADOS_BRUTOS_COMPLETO"
                    ),

                    "document_id": (
                        document_id
                    ),

                    "ocr_result_id": (
                        ocr_result_id
                    ),

                    "message": (
                        error_message
                    ),
                },
            }

            result["validacao_pipeline"] = {
                "pipeline": (
                    "DADOS_BRUTOS_COMPLETO"
                ),

                "pipeline_version": 2,

                "document_id": (
                    document_id
                ),

                "ocr_result_id": (
                    ocr_result_id
                ),

                "persistencia_ok": False,

                "pipeline_processado": False,

                "error": (
                    error_message
                ),
            }

            return result

    @staticmethod
    def _pipeline_documentos_pessoais(
        db: Session,
        document_id: int,
        ocr_result_id: int | None,
        prompt_categoria: str,
        dados: dict[str, object],
    ) -> dict[str, object]:

        result: dict[str, object] = {
            "success": False,
            "document_id": document_id,
            "ocr_result_id": ocr_result_id,
            "pipeline": "DOCUMENTOS_PESSOAIS",
            "categoria": prompt_categoria,
            "steps": {},
            "errors": [],
            "warnings": [],
        }

        try:

            doc = (
                db.query(Document)
                .filter(Document.id == document_id)
                .first()
            )

            if not doc:
                raise Exception(
                    "Documento não encontrado."
                )

            imovel = (
                db.query(Imovel)
                .filter(Imovel.project_id == doc.project_id)
                .first()
            )

            if not imovel:
                raise Exception(
                    "Projeto não possui imóvel vinculado."
                )

            # =====================================================
            # 🔥 EXTRAÇÃO PRINCIPAL
            # =====================================================
            pessoa = dados.get("pessoa")

            documentos = dados.get("documentos")

            payload_json = OcrPipelineService._json_safe(
                dados
            )

            pessoa_json = OcrPipelineService._json_safe(
                pessoa
            )

            documentos_json = (
                OcrPipelineService._json_safe(
                    documentos
                )
            )

            total_documentos = 0

            if isinstance(documentos_json, list):
                total_documentos = len(documentos_json)

            elif isinstance(documentos_json, dict):
                total_documentos = len(
                    documentos_json.keys()
                )

            # =====================================================
            # 🔥 QUALIDADE OCR
            # =====================================================
            qualidade_ocr = (
                dados.get("qualidade")
                if isinstance(dados, dict)
                else None
            )

            score_ocr = 0

            confianca_geral = None

            if isinstance(qualidade_ocr, dict):

                try:
                    score_ocr = int(
                        float(
                            qualidade_ocr.get("score")
                            or qualidade_ocr.get("confidence")
                            or 0
                        )
                    )
                except Exception:
                    score_ocr = 0

                confianca_geral = (
                    qualidade_ocr.get("confianca_geral")
                    or qualidade_ocr.get("confidence")
                )

            score_ocr = max(
                0,
                min(
                    100,
                    score_ocr,
                ),
            )

            # =====================================================
            # 🔥 VALIDAÇÃO
            # =====================================================
            possui_pessoa = bool(
                pessoa_json
            )

            possui_documentos = bool(
                documentos_json
            )

            # =====================================================
            # 🔥 GERAÇÃO DE ARQUIVOS FÍSICOS
            # =====================================================
            json_legivel = (
                OcrPipelineService._formatar_json_legivel(
                    payload_json
                )
            )

            txt_legivel = (
                "RELATÓRIO OCR - DOCUMENTOS PESSOAIS\n"
                "\n"
                f"DOCUMENT ID: {document_id}\n"
                f"OCR RESULT ID: {ocr_result_id}\n"
                f"CATEGORIA: {prompt_categoria}\n"
                f"TOTAL DOCUMENTOS: {total_documentos}\n"
                f"SCORE OCR: {score_ocr}\n"
                "\n"
                "====================================================\n"
                "DADOS PESSOAIS EXTRAÍDOS\n"
                "====================================================\n"
                "\n"
                f"{json_legivel}"
            )

            arquivo_json = (
                OcrPipelineService._salvar_arquivo_pipeline_ocr(
                    imovel_id=imovel.id,
                    pipeline="documentos_pessoais",
                    nome_base="documentos_pessoais",
                    extensao="json",
                    conteudo=json_legivel,
                )
            )

            arquivo_txt = (
                OcrPipelineService._salvar_arquivo_pipeline_ocr(
                    imovel_id=imovel.id,
                    pipeline="documentos_pessoais",
                    nome_base="documentos_pessoais_relatorio",
                    extensao="txt",
                    conteudo=txt_legivel,
                )
            )

            # =====================================================
            # 🔥 DOCUMENTO TÉCNICO
            # =====================================================
            documento_tecnico = create_documento_tecnico(
                db=db,
                imovel_id=imovel.id,
                data=DocumentoTecnicoCreate(
                    document_group_key=(
                        "OCR_DOCUMENTOS_PESSOAIS"
                    ),

                    tipo="OCR Documentos Pessoais",

                    status_tecnico="EM_ANALISE",

                    conteudo_texto=txt_legivel,

                    conteudo_json=payload_json,

                    arquivo_path=arquivo_json.get(
                        "arquivo_path"
                    ),

                    metadata_json={
                        "ocr_result_id": (
                            ocr_result_id
                        ),

                        "document_id": (
                            document_id
                        ),

                        "categoria": (
                            prompt_categoria
                        ),

                        "pipeline": (
                            "DOCUMENTOS_PESSOAIS"
                        ),

                        "pipeline_version": 2,

                        "possui_pessoa": (
                            possui_pessoa
                        ),

                        "possui_documentos": (
                            possui_documentos
                        ),

                        "total_documentos": (
                            total_documentos
                        ),

                        "qualidade_score": (
                            score_ocr
                        ),

                        "confianca_geral": (
                            confianca_geral
                        ),

                        "arquivos_gerados": {
                            "json": arquivo_json,
                            "txt": arquivo_txt,
                        },
                    },

                    gerado_em=datetime.utcnow(),
                ),
            )

            # =====================================================
            # 🔥 WARNING OCR
            # =====================================================
            if score_ocr < 60:

                warnings = result.get("warnings")

                if not isinstance(warnings, list):
                    warnings = []
                    result["warnings"] = warnings

                warnings.append(
                    (
                        "OCR com score reduzido "
                        f"(score={score_ocr})."
                    )
                )

            # =====================================================
            # 🔥 RESULTADO PRINCIPAL
            # =====================================================
            result["success"] = True

            result["steps"] = {
                "documentos_pessoais": {
                    "success": True,

                    "pipeline": (
                        "DOCUMENTOS_PESSOAIS"
                    ),

                    "pipeline_version": 2,

                    "documento_tecnico_id": (
                        documento_tecnico.id
                    ),

                    "document_group_key": (
                        "OCR_DOCUMENTOS_PESSOAIS"
                    ),

                    "tipo_documento": (
                        "OCR Documentos Pessoais"
                    ),

                    "imovel_id": (
                        imovel.id
                    ),

                    "document_id": (
                        document_id
                    ),

                    "ocr_result_id": (
                        ocr_result_id
                    ),

                    "pessoa": (
                        pessoa_json
                    ),

                    "documentos": (
                        documentos_json
                    ),

                    "possui_pessoa": (
                        possui_pessoa
                    ),

                    "possui_documentos": (
                        possui_documentos
                    ),

                    "total_documentos": (
                        total_documentos
                    ),

                    "payload_completo": (
                        payload_json
                    ),

                    "arquivo_json_path": (
                        arquivo_json.get(
                            "arquivo_path"
                        )
                    ),

                    "arquivo_json_url": (
                        arquivo_json.get(
                            "arquivo_url"
                        )
                    ),

                    "arquivo_txt_path": (
                        arquivo_txt.get(
                            "arquivo_path"
                        )
                    ),

                    "arquivo_txt_url": (
                        arquivo_txt.get(
                            "arquivo_url"
                        )
                    ),

                    "arquivos_gerados": {
                        "json": arquivo_json,
                        "txt": arquivo_txt,
                    },

                    "qualidade_score": (
                        score_ocr
                    ),

                    "confianca_geral": (
                        confianca_geral
                    ),

                    "message": (
                        "Documentos pessoais "
                        "processados, persistidos "
                        "e exportados com sucesso."
                    ),
                },
            }

            # =====================================================
            # 🔥 METADATA PIPELINE
            # =====================================================
            result["metadata_pipeline"] = {
                "pipeline": (
                    "DOCUMENTOS_PESSOAIS"
                ),

                "pipeline_version": 2,

                "engine_origem": (
                    "OCR_PIPELINE"
                ),

                "normalizador": (
                    "normalizar_dados_ocr"
                ),

                "categoria_prompt": (
                    prompt_categoria
                ),

                "document_group_key": (
                    "OCR_DOCUMENTOS_PESSOAIS"
                ),

                "document_id": (
                    document_id
                ),

                "ocr_result_id": (
                    ocr_result_id
                ),

                "imovel_id": (
                    imovel.id
                ),

                "documento_tecnico_id": (
                    documento_tecnico.id
                ),

                "arquivos_gerados": {
                    "json": arquivo_json,
                    "txt": arquivo_txt,
                },

                "pipeline_processado": True,

                "possui_pessoa": (
                    possui_pessoa
                ),

                "possui_documentos": (
                    possui_documentos
                ),
            }

            # =====================================================
            # 🔥 ESTATÍSTICAS
            # =====================================================
            result["estatisticas"] = {
                "total_documentos": (
                    total_documentos
                ),

                "score_ocr": (
                    score_ocr
                ),

                "confianca_geral": (
                    confianca_geral
                ),

                "possui_pessoa": (
                    possui_pessoa
                ),

                "possui_documentos": (
                    possui_documentos
                ),

                "total_campos_pessoa": (
                    len(pessoa_json)
                    if isinstance(
                        pessoa_json,
                        dict,
                    )
                    else 0
                ),

                "total_documentos_extraidos": (
                    len(documentos_json)
                    if isinstance(
                        documentos_json,
                        list,
                    )
                    else 0
                ),

                "arquivo_json_gerado": bool(
                    arquivo_json.get(
                        "arquivo_path"
                    )
                ),

                "arquivo_txt_gerado": bool(
                    arquivo_txt.get(
                        "arquivo_path"
                    )
                ),
            }

            # =====================================================
            # 🔥 VALIDAÇÃO PIPELINE
            # =====================================================
            result["validacao_pipeline"] = {
                "pipeline": (
                    "DOCUMENTOS_PESSOAIS"
                ),

                "pipeline_version": 2,

                "document_id": (
                    document_id
                ),

                "ocr_result_id": (
                    ocr_result_id
                ),

                "imovel_id": (
                    imovel.id
                ),

                "documento_tecnico_id": (
                    documento_tecnico.id
                ),

                "persistencia_ok": True,

                "payload_ok": bool(
                    payload_json
                ),

                "payload_tipo": (
                    type(payload_json).__name__
                ),

                "possui_pessoa": (
                    possui_pessoa
                ),

                "possui_documentos": (
                    possui_documentos
                ),

                "qualidade_score": (
                    score_ocr
                ),

                "qualidade_minima_ok": (
                    score_ocr >= 60
                ),

                "confianca_geral": (
                    confianca_geral
                ),

                "arquivo_json_gerado": bool(
                    arquivo_json.get(
                        "arquivo_path"
                    )
                ),

                "arquivo_txt_gerado": bool(
                    arquivo_txt.get(
                        "arquivo_path"
                    )
                ),

                "arquivo_json_path": (
                    arquivo_json.get(
                        "arquivo_path"
                    )
                ),

                "arquivo_txt_path": (
                    arquivo_txt.get(
                        "arquivo_path"
                    )
                ),

                "pipeline_processado": True,
            }

            return result

        except Exception as exc:

            OcrPipelineService._rollback_safely(db)

            error_message = str(exc)

            result["success"] = False

            result["errors"].append(
                error_message
            )

            result["steps"] = {
                "documentos_pessoais": {
                    "success": False,

                    "pipeline": (
                        "DOCUMENTOS_PESSOAIS"
                    ),

                    "document_id": (
                        document_id
                    ),

                    "ocr_result_id": (
                        ocr_result_id
                    ),

                    "message": (
                        error_message
                    ),
                },
            }

            result["validacao_pipeline"] = {
                "pipeline": (
                    "DOCUMENTOS_PESSOAIS"
                ),

                "pipeline_version": 2,

                "document_id": (
                    document_id
                ),

                "ocr_result_id": (
                    ocr_result_id
                ),

                "persistencia_ok": False,

                "pipeline_processado": False,

                "error": (
                    error_message
                ),
            }

            return result
        
    @staticmethod
    def _pipeline_ficha_cadastral_sig(
        db: Session,
        document_id: int,
        ocr_result_id: int | None,
        prompt_categoria: str,
        dados: dict[str, object],
    ) -> dict[str, object]:

        result: dict[str, object] = {
            "success": False,
            "document_id": document_id,
            "ocr_result_id": ocr_result_id,
            "pipeline": "FICHA_CADASTRAL_SIG",
            "categoria": prompt_categoria,
            "steps": {},
            "errors": [],
            "warnings": [],
        }

        try:

            doc = (
                db.query(Document)
                .filter(Document.id == document_id)
                .first()
            )

            if not doc:
                raise Exception(
                    "Documento não encontrado."
                )

            imovel = (
                db.query(Imovel)
                .filter(Imovel.project_id == doc.project_id)
                .first()
            )

            if not imovel:
                raise Exception(
                    "Projeto não possui imóvel vinculado."
                )

            # =====================================================
            # 🔥 EXTRAÇÃO PRINCIPAL
            # =====================================================
            ficha = (
                dados.get("ficha_cadastral")
                or dados.get("sig")
            )

            payload_json = OcrPipelineService._json_safe(
                dados
            )

            ficha_json = (
                OcrPipelineService._json_safe(
                    ficha
                )
            )

            total_campos_ficha = 0

            if isinstance(ficha_json, dict):
                total_campos_ficha = len(
                    ficha_json.keys()
                )

            elif isinstance(ficha_json, list):
                total_campos_ficha = len(
                    ficha_json
                )

            # =====================================================
            # 🔥 QUALIDADE OCR
            # =====================================================
            qualidade_ocr = (
                dados.get("qualidade")
                if isinstance(dados, dict)
                else None
            )

            score_ocr = 0

            confianca_geral = None

            if isinstance(qualidade_ocr, dict):

                try:
                    score_ocr = int(
                        float(
                            qualidade_ocr.get("score")
                            or qualidade_ocr.get("confidence")
                            or 0
                        )
                    )
                except Exception:
                    score_ocr = 0

                confianca_geral = (
                    qualidade_ocr.get("confianca_geral")
                    or qualidade_ocr.get("confidence")
                )

            score_ocr = max(
                0,
                min(
                    100,
                    score_ocr,
                ),
            )

            # =====================================================
            # 🔥 VALIDAÇÃO
            # =====================================================
            possui_ficha = bool(
                ficha_json
            )

            # =====================================================
            # 🔥 GERAÇÃO DE ARQUIVOS FÍSICOS
            # =====================================================
            json_legivel = (
                OcrPipelineService._formatar_json_legivel(
                    payload_json
                )
            )

            txt_legivel = (
                "RELATÓRIO OCR - FICHA CADASTRAL SIG\n"
                "\n"
                f"DOCUMENT ID: {document_id}\n"
                f"OCR RESULT ID: {ocr_result_id}\n"
                f"CATEGORIA: {prompt_categoria}\n"
                f"TOTAL CAMPOS FICHA: {total_campos_ficha}\n"
                f"SCORE OCR: {score_ocr}\n"
                "\n"
                "====================================================\n"
                "FICHA CADASTRAL EXTRAÍDA\n"
                "====================================================\n"
                "\n"
                f"{json_legivel}"
            )

            arquivo_json = (
                OcrPipelineService._salvar_arquivo_pipeline_ocr(
                    imovel_id=imovel.id,
                    pipeline="ficha_cadastral_sig",
                    nome_base="ficha_cadastral_sig",
                    extensao="json",
                    conteudo=json_legivel,
                )
            )

            arquivo_txt = (
                OcrPipelineService._salvar_arquivo_pipeline_ocr(
                    imovel_id=imovel.id,
                    pipeline="ficha_cadastral_sig",
                    nome_base="ficha_cadastral_sig_relatorio",
                    extensao="txt",
                    conteudo=txt_legivel,
                )
            )

            # =====================================================
            # 🔥 DOCUMENTO TÉCNICO
            # =====================================================
            documento_tecnico = create_documento_tecnico(
                db=db,
                imovel_id=imovel.id,
                data=DocumentoTecnicoCreate(
                    document_group_key=(
                        "OCR_FICHA_SIG"
                    ),

                    tipo="OCR Ficha Cadastral SIG",

                    status_tecnico="EM_ANALISE",

                    conteudo_texto=txt_legivel,

                    conteudo_json=payload_json,

                    arquivo_path=arquivo_json.get(
                        "arquivo_path"
                    ),

                    metadata_json={
                        "ocr_result_id": (
                            ocr_result_id
                        ),

                        "document_id": (
                            document_id
                        ),

                        "categoria": (
                            prompt_categoria
                        ),

                        "pipeline": (
                            "FICHA_CADASTRAL_SIG"
                        ),

                        "pipeline_version": 2,

                        "possui_ficha": (
                            possui_ficha
                        ),

                        "total_campos_ficha": (
                            total_campos_ficha
                        ),

                        "qualidade_score": (
                            score_ocr
                        ),

                        "confianca_geral": (
                            confianca_geral
                        ),

                        "arquivos_gerados": {
                            "json": arquivo_json,
                            "txt": arquivo_txt,
                        },
                    },

                    gerado_em=datetime.utcnow(),
                ),
            )

            # =====================================================
            # 🔥 WARNING OCR
            # =====================================================
            if score_ocr < 60:

                warnings = result.get("warnings")

                if not isinstance(warnings, list):
                    warnings = []
                    result["warnings"] = warnings

                warnings.append(
                    (
                        "OCR com score reduzido "
                        f"(score={score_ocr})."
                    )
                )

            # =====================================================
            # 🔥 RESULTADO PRINCIPAL
            # =====================================================
            result["success"] = True

            result["steps"] = {
                "ficha_sig": {
                    "success": True,

                    "pipeline": (
                        "FICHA_CADASTRAL_SIG"
                    ),

                    "pipeline_version": 2,

                    "documento_tecnico_id": (
                        documento_tecnico.id
                    ),

                    "document_group_key": (
                        "OCR_FICHA_SIG"
                    ),

                    "tipo_documento": (
                        "OCR Ficha Cadastral SIG"
                    ),

                    "imovel_id": (
                        imovel.id
                    ),

                    "document_id": (
                        document_id
                    ),

                    "ocr_result_id": (
                        ocr_result_id
                    ),

                    "dados_ficha": (
                        ficha_json
                    ),

                    "possui_ficha": (
                        possui_ficha
                    ),

                    "total_campos_ficha": (
                        total_campos_ficha
                    ),

                    "payload_completo": (
                        payload_json
                    ),

                    "arquivo_json_path": (
                        arquivo_json.get(
                            "arquivo_path"
                        )
                    ),

                    "arquivo_json_url": (
                        arquivo_json.get(
                            "arquivo_url"
                        )
                    ),

                    "arquivo_txt_path": (
                        arquivo_txt.get(
                            "arquivo_path"
                        )
                    ),

                    "arquivo_txt_url": (
                        arquivo_txt.get(
                            "arquivo_url"
                        )
                    ),

                    "arquivos_gerados": {
                        "json": arquivo_json,
                        "txt": arquivo_txt,
                    },

                    "qualidade_score": (
                        score_ocr
                    ),

                    "confianca_geral": (
                        confianca_geral
                    ),

                    "message": (
                        "Ficha cadastral SIG "
                        "processada, persistida "
                        "e exportada com sucesso."
                    ),
                },
            }

            # =====================================================
            # 🔥 METADATA PIPELINE
            # =====================================================
            result["metadata_pipeline"] = {
                "pipeline": (
                    "FICHA_CADASTRAL_SIG"
                ),

                "pipeline_version": 2,

                "engine_origem": (
                    "OCR_PIPELINE"
                ),

                "normalizador": (
                    "normalizar_dados_ocr"
                ),

                "categoria_prompt": (
                    prompt_categoria
                ),

                "document_group_key": (
                    "OCR_FICHA_SIG"
                ),

                "document_id": (
                    document_id
                ),

                "ocr_result_id": (
                    ocr_result_id
                ),

                "imovel_id": (
                    imovel.id
                ),

                "documento_tecnico_id": (
                    documento_tecnico.id
                ),

                "arquivos_gerados": {
                    "json": arquivo_json,
                    "txt": arquivo_txt,
                },

                "pipeline_processado": True,

                "possui_ficha": (
                    possui_ficha
                ),
            }

            # =====================================================
            # 🔥 ESTATÍSTICAS
            # =====================================================
            result["estatisticas"] = {
                "total_campos_ficha": (
                    total_campos_ficha
                ),

                "score_ocr": (
                    score_ocr
                ),

                "confianca_geral": (
                    confianca_geral
                ),

                "possui_ficha": (
                    possui_ficha
                ),

                "total_campos_extraidos": (
                    len(ficha_json)
                    if isinstance(
                        ficha_json,
                        dict,
                    )
                    else 0
                ),

                "arquivo_json_gerado": bool(
                    arquivo_json.get(
                        "arquivo_path"
                    )
                ),

                "arquivo_txt_gerado": bool(
                    arquivo_txt.get(
                        "arquivo_path"
                    )
                ),
            }

            # =====================================================
            # 🔥 VALIDAÇÃO PIPELINE
            # =====================================================
            result["validacao_pipeline"] = {
                "pipeline": (
                    "FICHA_CADASTRAL_SIG"
                ),

                "pipeline_version": 2,

                "document_id": (
                    document_id
                ),

                "ocr_result_id": (
                    ocr_result_id
                ),

                "imovel_id": (
                    imovel.id
                ),

                "documento_tecnico_id": (
                    documento_tecnico.id
                ),

                "persistencia_ok": True,

                "payload_ok": bool(
                    payload_json
                ),

                "payload_tipo": (
                    type(payload_json).__name__
                ),

                "possui_ficha": (
                    possui_ficha
                ),

                "qualidade_score": (
                    score_ocr
                ),

                "qualidade_minima_ok": (
                    score_ocr >= 60
                ),

                "confianca_geral": (
                    confianca_geral
                ),

                "arquivo_json_gerado": bool(
                    arquivo_json.get(
                        "arquivo_path"
                    )
                ),

                "arquivo_txt_gerado": bool(
                    arquivo_txt.get(
                        "arquivo_path"
                    )
                ),

                "arquivo_json_path": (
                    arquivo_json.get(
                        "arquivo_path"
                    )
                ),

                "arquivo_txt_path": (
                    arquivo_txt.get(
                        "arquivo_path"
                    )
                ),

                "pipeline_processado": True,
            }

            return result

        except Exception as exc:

            OcrPipelineService._rollback_safely(db)

            error_message = str(exc)

            result["success"] = False

            result["errors"].append(
                error_message
            )

            result["steps"] = {
                "ficha_sig": {
                    "success": False,

                    "pipeline": (
                        "FICHA_CADASTRAL_SIG"
                    ),

                    "document_id": (
                        document_id
                    ),

                    "ocr_result_id": (
                        ocr_result_id
                    ),

                    "message": (
                        error_message
                    ),
                },
            }

            result["validacao_pipeline"] = {
                "pipeline": (
                    "FICHA_CADASTRAL_SIG"
                ),

                "pipeline_version": 2,

                "document_id": (
                    document_id
                ),

                "ocr_result_id": (
                    ocr_result_id
                ),

                "persistencia_ok": False,

                "pipeline_processado": False,

                "error": (
                    error_message
                ),
            }

            return result

    @staticmethod
    def _pipeline_confrontantes_croqui(
        db: Session,
        document_id: int,
        ocr_result_id: int | None,
        prompt_categoria: str,
        dados: dict[str, object],
    ) -> dict[str, object]:

        result: dict[str, object] = {
            "success": False,
            "document_id": document_id,
            "ocr_result_id": ocr_result_id,
            "pipeline": "CONFRONTANTES_CROQUI",
            "categoria": prompt_categoria,
            "steps": {},
            "errors": [],
            "warnings": [],
        }

        try:

            doc = (
                db.query(Document)
                .filter(Document.id == document_id)
                .first()
            )

            if not doc:
                raise Exception(
                    "Documento não encontrado."
                )

            imovel = (
                db.query(Imovel)
                .filter(Imovel.project_id == doc.project_id)
                .first()
            )

            if not imovel:
                raise Exception(
                    "Projeto não possui imóvel vinculado."
                )

            confrontantes = (
                dados.get("confrontantes")
                or []
            )

            confrontantes_normalizados: list[
                dict[str, object | None]
            ] = []

            lados_detectados: list[str] = []

            matriculas_detectadas = 0

            cpfs_detectados = 0

            if isinstance(confrontantes, list):

                for item in confrontantes:

                    if not isinstance(item, dict):
                        continue

                    lado = (
                        OcrPipelineService
                        ._normalizar_texto_simples(
                            item.get("lado")
                            or item.get("direcao")
                        )
                    )

                    matricula = (
                        OcrPipelineService
                        ._normalizar_numero_matricula(
                            item.get("matricula")
                            or item.get(
                                "numero_matricula"
                            )
                        )
                    )

                    cpf_cnpj = (
                        OcrPipelineService
                        ._normalizar_texto_simples(
                            item.get("cpf_cnpj")
                        )
                    )

                    if lado:
                        lados_detectados.append(
                            lado
                        )

                    if matricula:
                        matriculas_detectadas += 1

                    if cpf_cnpj:
                        cpfs_detectados += 1

                    confrontantes_normalizados.append(
                        {
                            "lado": lado,

                            "lado_normalizado": (
                                OcrPipelineService
                                ._normalizar_texto_simples(
                                    item.get(
                                        "lado_normalizado"
                                    )
                                )
                            ),

                            "nome": (
                                OcrPipelineService
                                ._normalizar_texto_simples(
                                    item.get("nome")
                                )
                            ),

                            "descricao": (
                                OcrPipelineService
                                ._normalizar_texto_simples(
                                    item.get("descricao")
                                )
                            ),

                            "matricula": matricula,

                            "identificacao": (
                                OcrPipelineService
                                ._normalizar_texto_simples(
                                    item.get(
                                        "identificacao"
                                    )
                                )
                            ),

                            "cpf_cnpj": cpf_cnpj,

                            "tipo": (
                                OcrPipelineService
                                ._normalizar_texto_simples(
                                    item.get("tipo")
                                )
                            ),

                            "lote": (
                                OcrPipelineService
                                ._normalizar_texto_simples(
                                    item.get("lote")
                                )
                            ),

                            "gleba": (
                                OcrPipelineService
                                ._normalizar_texto_simples(
                                    item.get("gleba")
                                )
                            ),
                        }
                    )

            # =====================================================
            # 🔥 QUALIDADE OCR
            # =====================================================
            qualidade_ocr = (
                dados.get("qualidade")
                if isinstance(dados, dict)
                else None
            )

            score_ocr = 0

            confianca_geral = None

            if isinstance(qualidade_ocr, dict):

                try:
                    score_ocr = int(
                        float(
                            qualidade_ocr.get("score")
                            or qualidade_ocr.get("confidence")
                            or 0
                        )
                    )
                except Exception:
                    score_ocr = 0

                confianca_geral = (
                    qualidade_ocr.get(
                        "confianca_geral"
                    )
                    or qualidade_ocr.get(
                        "confidence"
                    )
                )

            score_ocr = max(
                0,
                min(
                    100,
                    score_ocr,
                ),
            )

            # =====================================================
            # 🔥 PAYLOAD FINAL
            # =====================================================
            payload_json = {
                "confrontantes": (
                    confrontantes_normalizados
                ),

                "payload_original": (
                    OcrPipelineService._json_safe(
                        dados
                    )
                ),
            }

            total_confrontantes = len(
                confrontantes_normalizados
            )

            lados_unicos = sorted(
                list(set(lados_detectados))
            )

            # =====================================================
            # 🔥 EXPORTAÇÃO JSON
            # =====================================================
            json_bytes = json.dumps(
                payload_json,
                ensure_ascii=False,
                indent=2,
            ).encode("utf-8")

            json_filename = (
                f"ocr_confrontantes_"
                f"{document_id}_"
                f"{int(datetime.utcnow().timestamp())}.json"
            )

            arquivo_json = (
                OcrPipelineService
                ._salvar_arquivo_pipeline(
                    project_id=doc.project_id,
                    folder_relative=(
                        "2_dados_imoveis_confrontantes"
                    ),
                    filename=json_filename,
                    content=json_bytes,
                )
            )

            # =====================================================
            # 🔥 RELATÓRIO TXT
            # =====================================================
            linhas_relatorio: list[str] = []

            linhas_relatorio.append(
                "RELATÓRIO DE CONFRONTANTES"
            )

            linhas_relatorio.append("")

            linhas_relatorio.append(
                f"DOCUMENT_ID: {document_id}"
            )

            linhas_relatorio.append(
                f"OCR_RESULT_ID: {ocr_result_id}"
            )

            linhas_relatorio.append(
                f"TOTAL DE CONFRONTANTES: "
                f"{total_confrontantes}"
            )

            linhas_relatorio.append("")

            if lados_unicos:

                linhas_relatorio.append(
                    "LADOS IDENTIFICADOS:"
                )

                for lado in lados_unicos:
                    linhas_relatorio.append(
                        f"- {lado}"
                    )

                linhas_relatorio.append("")

            for indice, confrontante in enumerate(
                confrontantes_normalizados,
                start=1,
            ):

                linhas_relatorio.append(
                    f"CONFRONTANTE {indice}"
                )

                linhas_relatorio.append(
                    "-" * 50
                )

                linhas_relatorio.append(
                    f"NOME: "
                    f"{confrontante.get('nome') or '-'}"
                )

                linhas_relatorio.append(
                    f"LADO: "
                    f"{confrontante.get('lado') or '-'}"
                )

                linhas_relatorio.append(
                    f"TIPO: "
                    f"{confrontante.get('tipo') or '-'}"
                )

                linhas_relatorio.append(
                    f"MATRÍCULA: "
                    f"{confrontante.get('matricula') or '-'}"
                )

                linhas_relatorio.append(
                    f"CPF/CNPJ: "
                    f"{confrontante.get('cpf_cnpj') or '-'}"
                )

                linhas_relatorio.append(
                    f"LOTE: "
                    f"{confrontante.get('lote') or '-'}"
                )

                linhas_relatorio.append(
                    f"GLEBA: "
                    f"{confrontante.get('gleba') or '-'}"
                )

                linhas_relatorio.append(
                    f"DESCRIÇÃO: "
                    f"{confrontante.get('descricao') or '-'}"
                )

                linhas_relatorio.append("")

            relatorio_txt = "\n".join(
                linhas_relatorio
            )

            txt_filename = (
                f"relatorio_confrontantes_"
                f"{document_id}_"
                f"{int(datetime.utcnow().timestamp())}.txt"
            )

            arquivo_txt = (
                OcrPipelineService
                ._salvar_arquivo_pipeline(
                    project_id=doc.project_id,
                    folder_relative=(
                        "2_dados_imoveis_confrontantes"
                    ),
                    filename=txt_filename,
                    content=relatorio_txt.encode(
                        "utf-8"
                    ),
                )
            )

            # =====================================================
            # 🔥 DOCUMENTOS DO FRONTEND
            # =====================================================
            documento_json = (
                OcrPipelineService
                ._registrar_documento_pipeline(
                    db=db,
                    project_id=doc.project_id,
                    doc_type=(
                        "OCR_CONFRONTANTES_JSON"
                    ),
                    stored_filename=(
                        arquivo_json[
                            "stored_filename"
                        ]
                    ),
                    original_filename=(
                        json_filename
                    ),
                    file_path=(
                        arquivo_json[
                            "relative_path"
                        ]
                    ),
                    content_type=(
                        "application/json"
                    ),
                    description=(
                        "OCR estruturado "
                        "de confrontantes."
                    ),
                )
            )

            documento_txt = (
                OcrPipelineService
                ._registrar_documento_pipeline(
                    db=db,
                    project_id=doc.project_id,
                    doc_type=(
                        "OCR_CONFRONTANTES_RELATORIO"
                    ),
                    stored_filename=(
                        arquivo_txt[
                            "stored_filename"
                        ]
                    ),
                    original_filename=(
                        txt_filename
                    ),
                    file_path=(
                        arquivo_txt[
                            "relative_path"
                        ]
                    ),
                    content_type=(
                        "text/plain"
                    ),
                    description=(
                        "Relatório textual "
                        "de confrontantes."
                    ),
                )
            )

            # =====================================================
            # 🔥 WARNING OCR
            # =====================================================
            if score_ocr < 60:

                warnings = result.get("warnings")

                if not isinstance(warnings, list):
                    warnings = []
                    result["warnings"] = warnings

                warnings.append(
                    (
                        "OCR com score reduzido "
                        f"(score={score_ocr})."
                    )
                )

            if total_confrontantes == 0:

                warnings = result.get("warnings")

                if not isinstance(warnings, list):
                    warnings = []
                    result["warnings"] = warnings

                warnings.append(
                    "Nenhum confrontante válido detectado."
                )

            # =====================================================
            # 🔥 DOCUMENTO TÉCNICO
            # =====================================================
            documento_tecnico = create_documento_tecnico(
                db=db,
                imovel_id=imovel.id,
                data=DocumentoTecnicoCreate(
                    document_group_key=(
                        "OCR_CONFRONTANTES_CROQUI"
                    ),

                    tipo=(
                        "OCR Confrontantes Croqui"
                    ),

                    status_tecnico=(
                        "EM_ANALISE"
                    ),

                    conteudo_texto=(
                        relatorio_txt
                    ),

                    conteudo_json=(
                        payload_json
                    ),

                    arquivo_path=(
                        arquivo_json[
                            "relative_path"
                        ]
                    ),

                    metadata_json={
                        "ocr_result_id": (
                            ocr_result_id
                        ),

                        "document_id": (
                            document_id
                        ),

                        "categoria": (
                            prompt_categoria
                        ),

                        "pipeline": (
                            "CONFRONTANTES_CROQUI"
                        ),

                        "pipeline_version": 2,

                        "document_group_key": (
                            "OCR_CONFRONTANTES_CROQUI"
                        ),

                        "total_confrontantes": (
                            total_confrontantes
                        ),

                        "lados_detectados": (
                            lados_unicos
                        ),

                        "matriculas_detectadas": (
                            matriculas_detectadas
                        ),

                        "cpfs_detectados": (
                            cpfs_detectados
                        ),

                        "qualidade_score": (
                            score_ocr
                        ),

                        "confianca_geral": (
                            confianca_geral
                        ),

                        "arquivos_gerados": {
                            "json": {
                                "document_id": (
                                    documento_json.id
                                ),

                                "stored_filename": (
                                    arquivo_json[
                                        "stored_filename"
                                    ]
                                ),

                                "relative_path": (
                                    arquivo_json[
                                        "relative_path"
                                    ]
                                ),

                                "content_type": (
                                    "application/json"
                                ),
                            },

                            "txt": {
                                "document_id": (
                                    documento_txt.id
                                ),

                                "stored_filename": (
                                    arquivo_txt[
                                        "stored_filename"
                                    ]
                                ),

                                "relative_path": (
                                    arquivo_txt[
                                        "relative_path"
                                    ]
                                ),

                                "content_type": (
                                    "text/plain"
                                ),
                            },
                        },

                        "frontend_outputs": {
                            "json_document_id": (
                                documento_json.id
                            ),

                            "txt_document_id": (
                                documento_txt.id
                            ),
                        },

                        "persistido_em": (
                            datetime.utcnow().isoformat()
                        ),
                    },

                    gerado_em=datetime.utcnow(),
                ),
            )

            # =====================================================
            # 🔥 RESULTADO
            # =====================================================
            result["success"] = True

            result["steps"] = {
                "confrontantes": {
                    "success": True,

                    "pipeline": (
                        "CONFRONTANTES_CROQUI"
                    ),

                    "pipeline_version": 2,

                    "documento_tecnico_id": (
                        documento_tecnico.id
                    ),

                    "document_group_key": (
                        "OCR_CONFRONTANTES_CROQUI"
                    ),

                    "tipo_documento": (
                        "OCR Confrontantes Croqui"
                    ),

                    "document_id": (
                        document_id
                    ),

                    "ocr_result_id": (
                        ocr_result_id
                    ),

                    "imovel_id": (
                        imovel.id
                    ),

                    "total": (
                        total_confrontantes
                    ),

                    "dados": (
                        confrontantes_normalizados
                    ),

                    "lados_detectados": (
                        lados_unicos
                    ),

                    "matriculas_detectadas": (
                        matriculas_detectadas
                    ),

                    "cpfs_detectados": (
                        cpfs_detectados
                    ),

                    "arquivo_json_path": (
                        arquivo_json.get(
                            "relative_path"
                        )
                    ),

                    "arquivo_txt_path": (
                        arquivo_txt.get(
                            "relative_path"
                        )
                    ),

                    "documento_json_id": (
                        documento_json.id
                    ),

                    "documento_txt_id": (
                        documento_txt.id
                    ),

                    "arquivos_gerados": {
                        "json": arquivo_json,
                        "txt": arquivo_txt,
                    },

                    "qualidade_score": (
                        score_ocr
                    ),

                    "confianca_geral": (
                        confianca_geral
                    ),

                    "message": (
                        "Confrontantes processados, "
                        "persistidos e exportados "
                        "com sucesso."
                    ),
                },
            }

            # =====================================================
            # 🔥 METADATA PIPELINE
            # =====================================================
            result["metadata_pipeline"] = {
                "pipeline": (
                    "CONFRONTANTES_CROQUI"
                ),

                "pipeline_version": 2,

                "engine_origem": (
                    "OCR_PIPELINE"
                ),

                "normalizador": (
                    "normalizar_dados_ocr"
                ),

                "categoria_prompt": (
                    prompt_categoria
                ),

                "document_group_key": (
                    "OCR_CONFRONTANTES_CROQUI"
                ),

                "document_id": (
                    document_id
                ),

                "ocr_result_id": (
                    ocr_result_id
                ),

                "documento_tecnico_id": (
                    documento_tecnico.id
                ),

                "imovel_id": (
                    imovel.id
                ),

                "total_confrontantes": (
                    total_confrontantes
                ),

                "lados_detectados": (
                    lados_unicos
                ),

                "arquivos_gerados": {
                    "json": arquivo_json,
                    "txt": arquivo_txt,
                },

                "frontend_documents": {
                    "json_document_id": (
                        documento_json.id
                    ),

                    "txt_document_id": (
                        documento_txt.id
                    ),
                },

                "pipeline_processado": True,
            }

            # =====================================================
            # 🔥 ESTATÍSTICAS
            # =====================================================
            result["estatisticas"] = {
                "total_confrontantes": (
                    total_confrontantes
                ),

                "lados_detectados": (
                    lados_unicos
                ),

                "matriculas_detectadas": (
                    matriculas_detectadas
                ),

                "cpfs_detectados": (
                    cpfs_detectados
                ),

                "score_ocr": (
                    score_ocr
                ),

                "confianca_geral": (
                    confianca_geral
                ),

                "arquivo_json_gerado": bool(
                    arquivo_json.get(
                        "relative_path"
                    )
                ),

                "arquivo_txt_gerado": bool(
                    arquivo_txt.get(
                        "relative_path"
                    )
                ),

                "documentos_frontend_gerados": {
                    "json": (
                        documento_json.id
                    ),

                    "txt": (
                        documento_txt.id
                    ),
                },

                "pipeline_processado": True,
            }

            # =====================================================
            # 🔥 VALIDAÇÃO PIPELINE
            # =====================================================
            result["validacao_pipeline"] = {
                "pipeline": (
                    "CONFRONTANTES_CROQUI"
                ),

                "pipeline_version": 2,

                "document_id": (
                    document_id
                ),

                "ocr_result_id": (
                    ocr_result_id
                ),

                "documento_tecnico_id": (
                    documento_tecnico.id
                ),

                "imovel_id": (
                    imovel.id
                ),

                "persistencia_ok": True,

                "payload_ok": bool(
                    payload_json
                ),

                "confrontantes_detectados": (
                    total_confrontantes > 0
                ),

                "qualidade_score": (
                    score_ocr
                ),

                "qualidade_minima_ok": (
                    score_ocr >= 60
                ),

                "confianca_geral": (
                    confianca_geral
                ),

                "arquivo_json_gerado": bool(
                    arquivo_json.get(
                        "relative_path"
                    )
                ),

                "arquivo_txt_gerado": bool(
                    arquivo_txt.get(
                        "relative_path"
                    )
                ),

                "documento_json_id": (
                    documento_json.id
                ),

                "documento_txt_id": (
                    documento_txt.id
                ),

                "pipeline_processado": True,
            }

            return result

        except Exception as exc:

            OcrPipelineService._rollback_safely(db)

            error_message = str(exc)

            result["success"] = False

            result["errors"].append(
                error_message
            )

            result["steps"] = {
                "confrontantes": {
                    "success": False,

                    "pipeline": (
                        "CONFRONTANTES_CROQUI"
                    ),

                    "document_id": (
                        document_id
                    ),

                    "ocr_result_id": (
                        ocr_result_id
                    ),

                    "message": (
                        error_message
                    ),
                },
            }

            result["validacao_pipeline"] = {
                "pipeline": (
                    "CONFRONTANTES_CROQUI"
                ),

                "pipeline_version": 2,

                "document_id": (
                    document_id
                ),

                "ocr_result_id": (
                    ocr_result_id
                ),

                "persistencia_ok": False,

                "pipeline_processado": False,

                "error": (
                    error_message
                ),
            }

            return result

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

        # =========================================================
        # 🔥 QUALIDADE OCR (UNIFICADA)
        # =========================================================
        qualidade_ocr = (
            dados.get("qualidade")
            if isinstance(dados, dict)
            else None
        )

        metadata_ocr = (
            dados.get("metadata")
            if isinstance(dados, dict)
            else None
        )

        ocr_metadata = (
            dados.get("ocr_metadata")
            if isinstance(dados, dict)
            else None
        )

        quality_data = (
            dados.get("quality")
            if isinstance(dados, dict)
            else None
        )

        score_ocr = 0

        confianca_geral = None

        origem_score = None

        # =========================================================
        # 🔥 QUALIDADE PADRÃO PIPELINE
        # =========================================================
        if isinstance(qualidade_ocr, dict):

            try:
                valor_score = (
                    qualidade_ocr.get("score")
                    or qualidade_ocr.get("score_ocr")
                    or qualidade_ocr.get("confidence")
                    or 0
                )

                score_ocr = int(float(valor_score))

                origem_score = "qualidade"

            except Exception:
                score_ocr = 0

            confianca_geral = (
                qualidade_ocr.get("confianca_geral")
                or qualidade_ocr.get("confidence")
                or qualidade_ocr.get("confidence_score")
            )

        # =========================================================
        # 🔥 FALLBACK → METADATA
        # =========================================================
        if score_ocr <= 0 and isinstance(metadata_ocr, dict):

            try:
                valor_score = (
                    metadata_ocr.get("score")
                    or metadata_ocr.get("ocr_score")
                    or metadata_ocr.get("confidence")
                    or metadata_ocr.get("confidence_score")
                    or 0
                )

                score_ocr = int(float(valor_score))

                origem_score = "metadata"

            except Exception:
                score_ocr = 0

            if not confianca_geral:
                confianca_geral = (
                    metadata_ocr.get("confianca_geral")
                    or metadata_ocr.get("confidence")
                    or metadata_ocr.get("confidence_score")
                )

        # =========================================================
        # 🔥 FALLBACK → OCR METADATA
        # =========================================================
        if score_ocr <= 0 and isinstance(ocr_metadata, dict):

            try:
                valor_score = (
                    ocr_metadata.get("score")
                    or ocr_metadata.get("ocr_score")
                    or ocr_metadata.get("confidence")
                    or 0
                )

                score_ocr = int(float(valor_score))

                origem_score = "ocr_metadata"

            except Exception:
                score_ocr = 0

            if not confianca_geral:
                confianca_geral = (
                    ocr_metadata.get("confianca_geral")
                    or ocr_metadata.get("confidence")
                )

        # =========================================================
        # 🔥 FALLBACK → QUALITY
        # =========================================================
        if score_ocr <= 0 and isinstance(quality_data, dict):

            try:
                valor_score = (
                    quality_data.get("score")
                    or quality_data.get("confidence")
                    or quality_data.get("ocr_score")
                    or 0
                )

                score_ocr = int(float(valor_score))

                origem_score = "quality"

            except Exception:
                score_ocr = 0

            if not confianca_geral:
                confianca_geral = (
                    quality_data.get("confianca_geral")
                    or quality_data.get("confidence")
                )

        # =========================================================
        # 🔥 SANITIZAÇÃO FINAL
        # =========================================================
        try:
            score_ocr = max(
                0,
                min(
                    100,
                    int(score_ocr),
                ),
            )
        except Exception:
            score_ocr = 0

        # =========================================================
        # 🔥 NOVO — CONTROLE DE SIGEF
        # =========================================================
        sigef_obrigatorio = bool(
            geometria
            and epsg_origem_atual
            and epsg_origem_atual > 0
        )

        # =========================================================
        # 🔥 REGRAS DE SUCESSO
        # =========================================================
        sucesso_base = (
            geometria_ok
            and memorial_ok
            and croqui_ok
            and cad_ok
        )

        if sigef_obrigatorio:
            sucesso_base = (
                sucesso_base
                and sigef_ok
            )

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
                    f"(score={score_ocr}), "
                    "porém pipeline permaneceu executável."
                )
            )

        # =========================================================
        # 🔥 SUCESSO FINAL REAL
        # =========================================================
        result["success"] = sucesso_base

        # =========================================================
        # 🔥 DEBUG / RASTREABILIDADE
        # =========================================================
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

            "origem_score": origem_score,

            "pipeline": "MATRICULA",

            "ocr_result_id": ocr_result_id,

            "document_id": document_id,
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

                if not isinstance(dados, dict):
                    logger.error(
                        "Payload inválido para resolução de GeoJSON."
                    )
                    return None

                if (
                    isinstance(parsed, dict)
                    and parsed.get("type") in ["Polygon", "MultiPolygon"]
                    and isinstance(parsed.get("coordinates"), list)
                ):
                    try:
                        from shapely.geometry import shape, mapping

                        geom = shape(parsed)

                        if geom.is_empty:
                            return None
                        
                        if not geom.is_valid:
                            try:
                                geom = geom.buffer(0)
                            except Exception:
                                return None


                        if geom.is_valid and not geom.is_empty:
                            # 🔥 RETORNA GEOMETRIA CORRIGIDA (CRÍTICO)
                            return json.dumps(
                                mapping(geom),
                                ensure_ascii=False,
                            )

                    except Exception as exc:
                        logger.warning(
                            "Falha validação shapely no GeoJSON OCR: %s",
                            str(exc),
                        )

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
                    logger.info(
                        "GeoJSON válido carregado da estrutura normalizada."
                    )
                    return geo_validado

            # ================= SEGMENTOS =================
            if (
                isinstance(segmentos, list)
                and len(segmentos) >= 3
            ):
                geojson_por_segmentos = OcrPipelineService._gerar_geojson_por_segmentos(
                    segmentos
                )

                if geojson_por_segmentos:
                    logger.info(
                        "GeoJSON reconstruído via segmentos OCR."
                    )
                    return geojson_por_segmentos

            # ================= MEMORIAL =================
            if (
                isinstance(memorial_texto, str)
                and len(memorial_texto.strip()) >= 30
            ):
                geojson_por_memorial = OcrPipelineService._gerar_geojson_por_memorial(
                    memorial_texto
                )

                if geojson_por_memorial:
                    logger.info(
                        "GeoJSON reconstruído via memorial OCR."
                    )
                    return geojson_por_memorial

        # =========================================================
        # 🔄 FALLBACK LEGADO
        # =========================================================
        geojson = dados.get("geojson")

        geojson_normalizado = OcrPipelineService._normalizar_geojson(geojson)

        if geojson_normalizado:
            geo_validado = _validar_geojson(geojson_normalizado)
            if geo_validado:
                logger.warning(
                    "GeoJSON legado utilizado após fallback."
                )
                return geo_validado

        # ================= SEGMENTOS LEGADO =================
        segmentos_memorial = dados.get("segmentos_memorial")

        if isinstance(segmentos_memorial, list) and segmentos_memorial:
            geojson_por_segmentos = OcrPipelineService._gerar_geojson_por_segmentos(
                segmentos_memorial
            )

            if geojson_por_segmentos:
                logger.warning(
                    "GeoJSON legado reconstruído via segmentos."
                )
                return geojson_por_segmentos

        # ================= MEMORIAL LEGADO =================
        memorial_texto = dados.get("memorial_texto")

        if isinstance(memorial_texto, str) and memorial_texto.strip():
            geojson_por_memorial = OcrPipelineService._gerar_geojson_por_memorial(
                memorial_texto
            )

            if geojson_por_memorial:
                logger.warning(
                    "GeoJSON legado reconstruído via memorial."
                )   
                return geojson_por_memorial

        logger.error(
            "Nenhuma fonte geométrica válida encontrada no OCR"
        )
        return None
    
    @staticmethod
    def _normalizar_geojson(geojson: Any) -> Optional[str]:
        if geojson is None:
            return None

        parsed = None

        if isinstance(geojson, list):
            logger.warning(
                "GeoJSON OCR recebido como lista inválida."
            )
            return None

        if isinstance(geojson, dict):
            parsed = geojson

        elif isinstance(geojson, str):
            texto = geojson.strip()

            if not texto:
                return None

            try:
                parsed = json.loads(texto)
            except Exception:
                logger.warning(
                    "GeoJSON inválido recebido do OCR."
                )
                return None

        if not isinstance(parsed, dict):
            return None

        # 🔥 VALIDAÇÃO ESTRUTURAL
        tipo = parsed.get("type")

        if tipo == "Feature":
            geometry = parsed.get("geometry")
            if not isinstance(geometry, dict):
                logger.warning(
                    "Feature OCR sem geometry válido."
                )   
                return None
            parsed = geometry
            tipo = parsed.get("type")

        elif tipo == "FeatureCollection":
            features = parsed.get("features")
            if not isinstance(features, list) or not features:
                logger.warning(
                    "FeatureCollection OCR sem features."
                )
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
                logger.warning(
                    "FeatureCollection sem geometria poligonal válida."
                )
                return None

            parsed = geometria_feature
            tipo = parsed.get("type")

        coords = parsed.get("coordinates")

        if coords is None:
            logger.warning(
                "GeoJSON OCR sem coordinates."
            )
            return None

        if tipo not in ["Polygon", "MultiPolygon"]:
            logger.warning(
                "GeoJSON OCR ignorado por tipo inválido."
            )
            return None

        if not isinstance(coords, list) or not coords:
            logger.warning(
                "GeoJSON OCR ignorado por coordinates inválido."
            )
            return None

        try:
            from shapely.geometry import shape

            geom = shape(parsed)

            if geom.is_empty:
                logger.warning(
                    "GeoJSON OCR gerou geometria vazia."
                )
                return None

            if not geom.is_valid:

                try:
                    geom = geom.buffer(0)

                except Exception:
                    logger.warning(
                        "Falha ao corrigir geometria OCR."
                    )
                    return None

            if geom.is_empty or not geom.is_valid:
                logger.warning(
                    "Geometria OCR inválida após correção."
                )
                return None

        except Exception as exc:
            logger.warning(
                "Falha validação shapely GeoJSON OCR: %s",
                str(exc),
            )
            return None

        try:

            logger.info(
                "GeoJSON OCR normalizado com sucesso."
            )

            return json.dumps(
                parsed,
                ensure_ascii=False,
            )

        except Exception as exc:

            logger.warning(
                "Falha serialização GeoJSON OCR: %s",
                str(exc),
            )

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

        distancias_processadas: list[float] = []
        segmentos_invalidos: list[str] = []
        segmentos_validos: int = 0

        minx = 0.0
        miny = 0.0
        maxx = 0.0
        maxy = 0.0

        ultimo_azimute: Optional[float] = None

        LIMITE_ABSOLUTO_SEGMENTO = 5000.0
        LIMITE_ENVELOPE = 50000.0
        LIMITE_SALTO_ANGULAR = 170.0
        LIMITE_INVALIDOS_PERCENTUAL = 0.35
        LIMITE_AREA_ABSURDA = 1_000_000_000.0
        LIMITE_COORDENADA_ABSURDA = 100_000_000.0
        LIMITE_MINIMO_SEGMENTOS = 3

        for index, seg in enumerate(segmentos_memorial, start=1):

            if not isinstance(seg, dict):
                segmentos_invalidos.append(
                    f"Segmento {index}: estrutura inválida"
                )
                continue

            angulo_raw = (
                seg.get("azimute")
                or seg.get("azimute_raw")
                or seg.get("rumo")
            )

            distancia_raw = seg.get("distancia")

            if angulo_raw is None or distancia_raw is None:
                segmentos_invalidos.append(
                    f"Segmento {index}: azimute ou distância ausente"
                )
                continue

            try:
                azimute = OcrPipelineService._parse_angulo_para_graus(
                    str(angulo_raw)
                )

                if azimute < 0 or azimute > 360:
                    raise ValueError(
                        "azimute fora do intervalo válido"
                    )

                distancia = OcrPipelineService._parse_distancia(
                    distancia_raw
                )

                if distancia <= 0:
                    raise ValueError(
                        "distância inválida"
                    )

            except Exception as exc:
                segmentos_invalidos.append(
                    f"Segmento {index}: {str(exc)} | "
                    f"azimute={angulo_raw} | "
                    f"distancia={distancia_raw}"
                )
                continue

            if distancia > LIMITE_ABSOLUTO_SEGMENTO:
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
                                distancia = distancia_corrigida
                                recuperado_por_ocr = True
                    else:
                        distancia = distancia_corrigida
                        recuperado_por_ocr = True

                if not recuperado_por_ocr:
                    segmentos_invalidos.append(
                        f"Segmento {index}: distância excessiva "
                        f"({distancia:.2f}m)"
                    )
                    continue

            if distancias_processadas:
                media_distancias = (
                    sum(distancias_processadas)
                    / len(distancias_processadas)
                )

                if media_distancias > 0:
                    fator_explosao = distancia / media_distancias

                    if fator_explosao > 25:
                        segmentos_invalidos.append(
                            f"Segmento {index}: explosão vetorial "
                            f"(x{fator_explosao:.2f})"
                        )
                        continue

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

            if (
                math.isnan(dx)
                or math.isnan(dy)
                or math.isinf(dx)
                or math.isinf(dy)
            ):
                segmentos_invalidos.append(
                    f"Segmento {index}: deslocamento inválido"
                )
                continue

            if abs(dx) > 1e7 or abs(dy) > 1e7:
                segmentos_invalidos.append(
                    f"Segmento {index}: deslocamento absurdo"
                )
                continue

            novo_x = x + dx
            novo_y = y + dy

            if (
                abs(novo_x) > LIMITE_COORDENADA_ABSURDA
                or abs(novo_y) > LIMITE_COORDENADA_ABSURDA
            ):
                segmentos_invalidos.append(
                    f"Segmento {index}: coordenada absoluta inválida"
                )
                continue

            minx = min(minx, novo_x)
            miny = min(miny, novo_y)

            maxx = max(maxx, novo_x)
            maxy = max(maxy, novo_y)

            spanx = abs(maxx - minx)
            spany = abs(maxy - miny)

            if spanx > LIMITE_ENVELOPE or spany > LIMITE_ENVELOPE:
                segmentos_invalidos.append(
                    f"Segmento {index}: envelope inválido "
                    f"({spanx:.2f} x {spany:.2f})"
                )
                continue

            x = novo_x
            y = novo_y

            coords.append((x, y))
            distancias_processadas.append(distancia)
            segmentos_validos += 1

        total_segmentos = len(segmentos_memorial)

        if segmentos_invalidos:
            print(
                "⚠️ Segmentos OCR descartados: "
                f"{len(segmentos_invalidos)}/{total_segmentos}"
            )

            for item in segmentos_invalidos[:10]:
                print(f"   - {item}")

        if (
            segmentos_validos < LIMITE_MINIMO_SEGMENTOS
            or len(coords) < 4
        ):
            print(
                "⚠️ Segmentos válidos insuficientes "
                "para formar polígono"
            )
            return None

        percentual_invalidos = (
            len(segmentos_invalidos) / total_segmentos
            if total_segmentos > 0
            else 1
        )

        if percentual_invalidos > LIMITE_INVALIDOS_PERCENTUAL:
            print(
                "⚠️ Geometria rejeitada: excesso de segmentos "
                f"inválidos ({percentual_invalidos:.2%})"
            )
            return None

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

        if polygon.area <= 0:
            print("⚠️ Área geométrica inválida")
            return None

        if polygon.area > LIMITE_AREA_ABSURDA:
            print(
                "⚠️ Área geométrica absurda detectada"
            )
            return None

        try:
            from shapely.geometry import mapping

            geojson_final = mapping(polygon)

            perimetro = float(polygon.length)

            indice_compacidade = 0.0

            try:
                if perimetro > 0:
                    indice_compacidade = float(
                        (4 * math.pi * polygon.area)
                        / (perimetro ** 2)
                    )

            except Exception:
                 indice_compacidade = 0.0

            # =====================================================
            # SCORE GEOMÉTRICO
            # =====================================================
            score_geometrico = 100.0

            try:
                penalidade_fechamento = min(
                    45.0,
                    float(erro_fechamento) * 4.0,
                )

                percentual_invalidos = (
                    len(segmentos_invalidos) / total_segmentos
                    if total_segmentos > 0
                    else 1.0
                )

                penalidade_invalidos = min(
                    35.0,
                    percentual_invalidos * 100.0,
                )

                penalidade_poligono = 0.0

                if not polygon.is_valid:
                    penalidade_poligono += 20.0

                if polygon.area <= 0:
                    penalidade_poligono += 40.0

                score_geometrico = max(
                    0.0,
                    min(
                        100.0,
                        100.0
                        - penalidade_fechamento
                        - penalidade_invalidos
                        - penalidade_poligono,
                    ),
                )

            except Exception:
                score_geometrico = 0.0

            geojson_final["metadata"] = {
                "referencial": "LOCAL_CARTESIANO",
                "origem": "SEGMENTOS_MEMORIAL",
                "reconstruido_por_ocr": True,
                "possui_georreferenciamento_real": False,
                "tipo_geometria": "POLIGONO_RECONSTRUIDO",
                "engine": "OCR_PIPELINE",
                "score_geometrico": round(
                    float(score_geometrico),
                    2,
                ),
                "modo_recuperacao": (
                    "OCR_HEURISTICO"
                    if segmentos_invalidos
                    else "PADRAO"
                ),
                "segmentos_recebidos": total_segmentos,
                "segmentos_validos": segmentos_validos,
                "segmentos_invalidos": len(segmentos_invalidos),
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

        texto = re.sub(
            r"[ \t]+",
            " ",
            texto,
        )

        texto = re.sub(
            r"\n{3,}",
            "\n\n",
            texto,
        )

        resultado: Optional[dict[str, Any]] = None

        # =========================================================
        # 🔥 TENTATIVA PRINCIPAL
        # =========================================================
        try:

            resultado = MemorialParserService.gerar_geometria(
                texto
            )

        except Exception as exc:

            print(
                "⚠️ Falha principal ao gerar geometria "
                f"do memorial: {str(exc)}"
            )

            # =====================================================
            # 🔥 FALLBACK OCR TOLERANTE
            # =====================================================
            try:

                texto_recuperado = texto

                # ================================================
                # OCR decimal colapsado
                # 9195040 -> 91°95'04"
                # ================================================
                texto_recuperado = re.sub(
                    r"\b(\d{2})(\d{2})(\d{2})\b",
                    r"\1°\2'\3\"",
                    texto_recuperado,
                )

                texto_recuperado = re.sub(
                    r"\b(\d{3})(\d{2})(\d{2})\b",
                    r"\1°\2'\3\"",
                    texto_recuperado,
                )

                resultado = (
                    MemorialParserService.gerar_geometria(
                        texto_recuperado
                    )
                )

                logger.info(
                    "Memorial recuperado via heurística OCR."
                )

            except Exception as exc2:

                print(
                    "⚠️ Fallback memorial falhou: "
                    f"{str(exc2)}"
                )

                return None

        if not resultado:
            return None

        geojson = resultado.get("geojson")

        # =========================================================
        # 🔥 VALIDAÇÃO ESTRUTURAL
        # =========================================================
        if (
            not isinstance(geojson, dict)
            or geojson.get("type")
            not in ["Polygon", "MultiPolygon"]
            or not isinstance(
                geojson.get("coordinates"),
                list,
            )
        ):

            print(
                "⚠️ GeoJSON do memorial inválido"
            )

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

                try:

                    geom_corrigida = geom.buffer(0)

                    if (
                        not geom_corrigida.is_empty
                        and geom_corrigida.is_valid
                    ):
                        geom = geom_corrigida

                except Exception:
                    pass

            # =====================================================
            # 🔥 MULTIPOLYGON OCR
            # =====================================================
            if geom.geom_type == "MultiPolygon":

                try:

                    geoms = list(geom.geoms)

                    if not geoms:

                        print(
                            "⚠️ MultiPolygon vazio"
                        )

                        return None

                    geoms.sort(
                        key=lambda g: g.area,
                        reverse=True,
                    )

                    geom = geoms[0]

                    print(
                        "⚠️ MultiPolygon reduzido "
                        "para maior polígono"
                    )

                except Exception:

                    print(
                        "⚠️ Falha ao recuperar "
                        "MultiPolygon"
                    )

                    return None

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
            # 🔥 ÁREA INVÁLIDA
            # =====================================================
            if (
                geom.area
                > OcrPipelineService.LIMITE_AREA_ABSURDA
            ):
                
                logger.warning(
                    "Geometria do memorial "
                    "possui área absurda."
                )

                return None

            # =====================================================
            # 🔥 EXTERIOR
            # =====================================================
            exterior_coords = list(
                geom.exterior.coords
            )

            if len(exterior_coords) < 4:

                primeiro_ponto = exterior_coords[0]
                ultimo_ponto = exterior_coords[-1]

                erro_fechamento = math.dist(
                    primeiro_ponto,
                    ultimo_ponto,
                )

                if (
                    erro_fechamento
                    > OcrPipelineService
                    .FECHAMENTO_TOLERANCIA_METROS
                ):
                    logger.warning(
                        "Memorial OCR possui erro "
                        "de fechamento elevado."
                    )

                    return None

            # =====================================================
            # 🔥 BBOX
            # =====================================================
            minx, miny, maxx, maxy = geom.bounds

            spanx = abs(maxx - minx)
            spany = abs(maxy - miny)

            # =====================================================
            # 🔥 GEOJSON FINAL
            # =====================================================
            geojson_final = mapping(geom)

            geojson_final["metadata"] = {
                "referencial": "LOCAL_CARTESIANO",
                "origem": "MEMORIAL_DESCRITIVO",
                "reconstruido_por_ocr": True,
                "possui_georreferenciamento_real": False,
                "tipo_geometria": "POLIGONO_RECONSTRUIDO",
                "engine": "OCR_PIPELINE",

                "pipeline": "MEMORIAL_OCR",

                "origem_parser": (
                    "MemorialParserService"
                ),

                "modo_recuperacao": "OCR_HEURISTICO",

                "memorial_processado": True,

                "geom_type": geom.geom_type,

                "vertices": len(exterior_coords) - 1,

                "erro_fechamento_metros": round(
                    float(erro_fechamento),
                    6,
                ),

                "fechamento_tolerancia_metros": (
                    OcrPipelineService
                    .FECHAMENTO_TOLERANCIA_METROS
                ),

                "area_modelo": round(
                    float(geom.area),
                    6,
                ),

                "bbox": {
                    "minx": round(minx, 6),
                    "miny": round(miny, 6),
                    "maxx": round(maxx, 6),
                    "maxy": round(maxy, 6),
                    "spanx": round(spanx, 6),
                    "spany": round(spany, 6),
                },
            }

            return json.dumps(
                geojson_final,
                ensure_ascii=False,
                default=float,
            )

        except Exception as exc:

           logger.exception(
                "Falha ao validar geometria "
                "gerada pelo memorial OCR."
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
        # 🔥 OCR CORROMPIDO — RECUPERAÇÃO CONTROLADA
        # =========================================================

        numeros = re.sub(
            r"\D",
            "",
            valor_limpo,
        )

        # =====================================================
        # FORMATO:
        # 9195040
        # -> 91°95'04"
        # =====================================================
        if len(numeros) == 7:

            try:

                g = float(numeros[:3])
                m = float(numeros[3:5])
                s = float(numeros[5:7])

                # =============================================
                # OCR frequentemente explode minutos
                # Ex: 95 -> 59
                # =============================================
                if m >= 60:

                    if str(int(m)).startswith("9"):
                        m = 59

                    else:
                        raise ValueError(
                            "Minutos inválidos"
                        )

                if s >= 60:

                    if str(int(s)).startswith("9"):
                        s = 59

                    else:
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

                if 0 <= decimal <= 360:

                    print(
                        "⚠️ Azimute OCR recuperado "
                        f"automaticamente: {valor_original}"
                    )

                    return decimal

            except Exception:
                pass

        # =====================================================
        # FORMATO:
        # 919504
        # -> 91°95'04"
        # =====================================================
        if len(numeros) == 6:

            try:

                g = float(numeros[:2])
                m = float(numeros[2:4])
                s = float(numeros[4:6])

                if m >= 60:

                    if str(int(m)).startswith("9"):
                        m = 59

                    else:
                        raise ValueError(
                            "Minutos inválidos"
                        )

                if s >= 60:

                    if str(int(s)).startswith("9"):
                        s = 59

                    else:
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

                if 0 <= decimal <= 360:

                    print(
                        "⚠️ Azimute OCR recuperado "
                        f"automaticamente: {valor_original}"
                    )

                    return decimal

            except Exception:
                pass

        # =====================================================
        # FALHA FINAL
        # =====================================================
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
        # 🔥 OCR SEM SEPARADOR DECIMAL
        # =========================================================
        #
        # Exemplos:
        #
        # 10522  -> 105.22
        # 9403   -> 94.03
        #
        # Aplicado SOMENTE em valores
        # absurdamente altos para perímetro rural.
        #
        # =========================================================
        if (
            "." not in numero_str
            and "," not in numero_str
            and numero_str.isdigit()
        ):

            if len(numero_str) >= 4:

                valor_inteiro = int(numero_str)

                # =============================================
                # heurística OCR controlada
                # =============================================
                if valor_inteiro > 5000:

                    decimal_recuperado = (
                        f"{numero_str[:-2]}.{numero_str[-2:]}"
                    )

                    try:

                        valor_teste = float(
                            decimal_recuperado
                        )

                        if 0.5 <= valor_teste <= 5000:

                            print(
                                "⚠️ Distância OCR "
                                "recuperada automaticamente: "
                                f"{numero_str} -> "
                                f"{decimal_recuperado}"
                            )

                            numero_str = decimal_recuperado

                    except Exception:
                        pass

        # =========================================================
        # 🔥 OCR DECIMAL DUPLICADO
        # =========================================================
        numero_str = re.sub(
            r"[.]{2,}",
            ".",
            numero_str,
        )

        numero_str = re.sub(
            r"[,]{2,}",
            ",",
            numero_str,
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
