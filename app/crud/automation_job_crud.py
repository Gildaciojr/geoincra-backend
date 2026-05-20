from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.models.automation_job import AutomationJob
from app.models.ocr_prompt import OcrPrompt
from app.models.ocr_result import OcrResult
from app.services.ocr_pipeline_service import (
    OcrPipelineService,
)

# =========================================================
# PIPELINES OCR
# =========================================================

PIPELINES_OCR = {
    "MATRICULA": {
        "parser": "MatriculaOCRParser",
        "normalizador": "normalizar_dados_ocr",
        "prioridade": "HIGH",
    },

    "DOCUMENTO_PESSOAL": {
        "parser": "DocumentoPessoalOCRParser",
        "normalizador": "normalizar_documento_pessoal",
        "prioridade": "HIGH",
    },

    "FICHA_CADASTRAL_SIG": {
        "parser": "FichaCadastralSIGParser",
        "normalizador": "normalizar_ficha_sig",
        "prioridade": "HIGH",
    },

    "CONFRONTANTES_CROQUI": {
        "parser": "ConfrontantesCroquiParser",
        "normalizador": "normalizar_confrontantes_croqui",
        "prioridade": "MEDIUM",
    },

    "DADOS_BRUTOS": {
        "parser": "RawDocumentOCRParser",
        "normalizador": "normalizar_documento_bruto",
        "prioridade": "LOW",
    },

    "MEMORIAL_DESCRITIVO": {
        "parser": "MemorialOCRParser",
        "normalizador": "normalizar_memorial_ocr",
        "prioridade": "HIGH",
    },
}


# =========================================================
# RESOLVE PIPELINE
# =========================================================
def _resolver_pipeline(
    categoria: str,
) -> Dict[str, Any]:

    categoria_normalizada = (
        OcrPipelineService._normalizar_categoria(
            categoria
        )
    )

    categorias_matricula = {
        "matricula",
        "matricula_imovel",
        "analise_matricula",
        "analise_matricula_completa",
        "analise_de_matricula_de_imovel",
        "analise_tecnica_completa_de_matricula",
    }

    categorias_documentos = {
        "documento_pessoal",
        "documentos_pessoais",
        "extracao_documentos_pessoais",
        "extracao_de_documentos_pessoais",
        "rg_cpf_cnh",
    }

    categorias_sig = {
        "ficha_cadastral_sig",
        "ficha_imovel_sig",
        "ficha_cadastral_de_imovel_sig",
        "ficha_cadastral_imovel_sig",
        "sig",
        "cadastro_sig",
        "cadastro_imovel_sig",
    }

    categorias_confrontantes = {
        "confrontantes_croqui",
        "insercao_confrontantes_croqui",
        "insercao_de_confrontantes_no_croqui",
        "inserir_confrontantes_no_croqui",
        "croqui_confrontantes",
    }

    categorias_dados_brutos = {
        "dados_brutos",
        "dados_brutos_completo",
        "dados_brutos_de_documentos",
        "dados_brutos_do_documento",
        "extracao_dados_brutos",
        "extracao_bruta",
    }

    if categoria_normalizada in categorias_matricula:
        return PIPELINES_OCR["MATRICULA"]

    if categoria_normalizada in categorias_documentos:
        return PIPELINES_OCR["DOCUMENTO_PESSOAL"]

    if categoria_normalizada in categorias_sig:
        return PIPELINES_OCR["FICHA_CADASTRAL_SIG"]

    if categoria_normalizada in categorias_confrontantes:
        return PIPELINES_OCR["CONFRONTANTES_CROQUI"]

    if categoria_normalizada in categorias_dados_brutos:
        return PIPELINES_OCR["DADOS_BRUTOS"]

    return {
        "parser": "GenericOCRParser",
        "normalizador": "normalizar_documento_generico",
        "prioridade": "LOW",
    }


# =========================================================
# CREATE OCR JOB
# =========================================================
def create_ocr_job(
    db: Session,

    user_id: int,

    project_id: int,

    document_id: int,

    prompt_id: int,

    ocr_result_id: int,
) -> AutomationJob:

    # =====================================================
    # OCR RESULT
    # =====================================================
    ocr_result = (
        db.query(OcrResult)
        .filter(OcrResult.id == ocr_result_id)
        .first()
    )

    if not ocr_result:
        raise Exception(
            "OCR result não encontrado."
        )

    # =====================================================
    # PROMPT OCR
    # =====================================================
    prompt = (
        db.query(OcrPrompt)
        .filter(OcrPrompt.id == prompt_id)
        .first()
    )

    if not prompt:
        raise Exception(
            "Prompt OCR não encontrado."
        )

    categoria = (
        OcrPipelineService._normalizar_categoria(
            prompt.categoria or ""
        )
    )

    # =====================================================
    # PIPELINE
    # =====================================================
    pipeline = _resolver_pipeline(
        categoria
    )

    parser = pipeline["parser"]

    normalizador = pipeline["normalizador"]

    prioridade = pipeline["prioridade"]

    # =====================================================
    # PAYLOAD OCR
    # =====================================================
    payload: Dict[str, Any] = {

        # -------------------------------------------------
        # CONTEXTO
        # -------------------------------------------------
        "document_id": document_id,

        "project_id": project_id,

        "ocr_result_id": ocr_result_id,

        "prompt_id": prompt_id,

        # -------------------------------------------------
        # OCR
        # -------------------------------------------------
        "provider": ocr_result.provider,

        "pipeline_tipo": categoria,

        "parser": parser,

        "normalizador": normalizador,

        # -------------------------------------------------
        # ENGINE
        # -------------------------------------------------
        "engine_version": "OCR_ENGINE_V2",

        "parser_version": "PARSER_V2",

        "normalizer_version": "NORMALIZER_V2",

        "schema_version": "SCHEMA_V2",

        # -------------------------------------------------
        # FLAGS
        # -------------------------------------------------
        "persistir_documentos_tecnicos": True,

        "executar_validacao_tecnica": True,

        "executar_parser_semantico": True,

        "executar_normalizacao": True,

        "executar_pos_processamento": True,

        "executar_auditoria": True,

        # -------------------------------------------------
        # RETRY
        # -------------------------------------------------
        "retry_count": 0,

        "retry_limit": 3,

        # -------------------------------------------------
        # EXECUÇÃO
        # -------------------------------------------------
        "priority": prioridade,
    }

    # =====================================================
    # JOB
    # =====================================================
    job = AutomationJob(

        user_id=user_id,

        project_id=project_id,

        type="OCR_DOCUMENT",

        status="PENDING",

        payload_json=payload,
    )

    db.add(job)

    # =====================================================
    # OCR RESULT
    # =====================================================
    ocr_result.pipeline_tipo = categoria

    ocr_result.parser_utilizado = parser

    ocr_result.normalizador_utilizado = (
        normalizador
    )

    ocr_result.engine_version = (
        "OCR_ENGINE_V2"
    )

    ocr_result.parser_version = (
        "PARSER_V2"
    )

    ocr_result.normalizer_version = (
        "NORMALIZER_V2"
    )

    ocr_result.schema_version = (
        "SCHEMA_V2"
    )

    db.commit()

    db.refresh(job)

    return job