from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# =========================================================
# REQUEST OCR
# =========================================================
class OcrRequest(BaseModel):

    # =====================================================
    # DOCUMENTO
    # =====================================================
    document_id: int = Field(
        ...,
        gt=0,
    )

    # =====================================================
    # ENGINE OCR
    # =====================================================
    provider: str = Field(
        default="GOOGLE",
        min_length=2,
        max_length=80,
    )

    # =====================================================
    # RESOLUÇÃO DE PROMPT
    # =====================================================
    prompt_id: Optional[int] = Field(
        default=None,
        gt=0,
    )

    prompt_slug: Optional[str] = Field(
        default=None,
        max_length=120,
    )

    pipeline: Optional[str] = Field(
        default=None,
        max_length=120,
    )

    categoria: Optional[str] = Field(
        default=None,
        max_length=120,
    )

    # =====================================================
    # CONFIGURAÇÃO EXECUÇÃO
    # =====================================================
    forcar_reprocessamento: bool = False

    persistir_resultado: bool = True

    gerar_geojson: bool = False

    gerar_memorial: bool = False

    gerar_documentos_tecnicos: bool = False

    gerar_confrontantes: bool = False

    gerar_historico_registral: bool = False

    habilitar_validacao_semantica: bool = True

    habilitar_pos_processamento: bool = True

    # =====================================================
    # CONFIG EXTRA
    # =====================================================
    configuracao_execucao: Optional[
        Dict[str, Any]
    ] = None


# =========================================================
# RESPONSE OCR
# =========================================================
class OcrResponse(BaseModel):

    # =====================================================
    # IDENTIFICAÇÃO
    # =====================================================
    id: int

    document_id: int

    status: str

    provider: str

    # =====================================================
    # PIPELINE
    # =====================================================
    pipeline: Optional[str] = None

    engine: Optional[str] = None

    modelo_llm: Optional[str] = None

    prompt_id: Optional[int] = None

    prompt_slug: Optional[str] = None

    prompt_nome: Optional[str] = None

    # =====================================================
    # TEXTO OCR
    # =====================================================
    texto_extraido: Optional[str] = None

    # =====================================================
    # JSON ESTRUTURADO
    # =====================================================
    dados_extraidos_json: Optional[
        Dict[str, Any]
    ] = None

    # =====================================================
    # FLAGS TÉCNICAS
    # =====================================================
    possui_geojson: bool = False

    possui_memorial: bool = False

    possui_confrontantes: bool = False

    possui_historico_registral: bool = False

    possui_proprietarios: bool = False

    possui_documentos_pessoais: bool = False

    possui_dados_sigef: bool = False

    possui_croqui: bool = False

    # =====================================================
    # QUALIDADE
    # =====================================================
    score_qualidade: Optional[int] = None

    warnings: List[str] = []

    erros_validacao: List[str] = []

    # =====================================================
    # PROCESSAMENTO
    # =====================================================
    tempo_processamento_ms: Optional[int] = None

    versao_pipeline: Optional[int] = None

    # =====================================================
    # ERRO
    # =====================================================
    erro: Optional[str] = None

    erro_detalhado: Optional[str] = None

    traceback_erro: Optional[str] = None

    # =====================================================
    # METADATA
    # =====================================================
    metadata_json: Optional[
        Dict[str, Any]
    ] = None

    # =====================================================
    # TIMESTAMPS
    # =====================================================
    created_at: datetime

    updated_at: datetime

    class Config:
        from_attributes = True