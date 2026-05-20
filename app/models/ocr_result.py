from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    Index,
)

from sqlalchemy.orm import relationship

from sqlalchemy.dialects.postgresql import JSONB

from app.core.database import Base


class OcrResult(Base):
    __tablename__ = "ocr_results"

    __table_args__ = (
        # =========================================================
        # PERFORMANCE / BUSCA
        # =========================================================
        Index("ix_ocr_result_document_status", "document_id", "status"),
        Index("ix_ocr_result_pipeline_tipo", "pipeline_tipo"),
        Index("ix_ocr_result_provider", "provider"),
        Index("ix_ocr_result_prompt", "ocr_prompt_id"),
        Index("ix_ocr_result_created_at", "created_at"),
    )

    id = Column(
        Integer,
        primary_key=True,
        index=True,
    )

    # =========================================================
    # RELACIONAMENTOS PRINCIPAIS
    # =========================================================

    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 🔥 NOVO — prompt utilizado
    ocr_prompt_id = Column(
        Integer,
        ForeignKey("ocr_prompts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    prompt_nome = Column(
        String(255),
        nullable=True,
    )

    prompt_slug = Column(
        String(120),
        nullable=True,
        index=True,
    )

 

    # =========================================================
    # EXECUÇÃO OCR
    # =========================================================

    status = Column(
        String(30),
        nullable=False,
        default="PENDING",
        comment=(
            "PENDING | PROCESSING | DONE | "
            "ERROR | PARTIAL | VALIDATED"
        ),
    )

    provider = Column(
        String(50),
        nullable=False,
        default="NONE",
        comment=(
            "AWS_TEXTRACT | GOOGLE | "
            "AZURE | OPENAI | GEMINI | NONE"
        ),
    )

    # =========================================================
    # 🔥 NOVO — PIPELINE OCR
    # =========================================================

    pipeline_tipo = Column(
        String(50),
        nullable=False,
        default="MATRICULA",
        index=True,
        comment=(
            "MATRICULA | DOCUMENTO_PESSOAL | "
            "FICHA_CADASTRAL_SIG | "
            "CONFRONTANTES_CROQUI | "
            "DADOS_BRUTOS | "
            "MEMORIAL_DESCRITIVO"
        ),
    )

    pipeline_versao = Column(
        String(80),
        nullable=True,
    )

    # =========================================================
    # 🔥 NOVO — VERSIONAMENTO DE ENGINE
    # =========================================================

    engine_version = Column(
        String(50),
        nullable=True,
        comment="Versão da engine OCR",
    )

    parser_version = Column(
        String(50),
        nullable=True,
        comment="Versão do parser registral/semântico",
    )

    normalizer_version = Column(
        String(50),
        nullable=True,
        comment="Versão do normalizador OCR",
    )

    schema_version = Column(
        String(50),
        nullable=True,
        comment="Versão do schema estruturado OCR",
    )

    # =========================================================
    # 🔥 NOVO — SCORE DE QUALIDADE
    # =========================================================

    score_extracao = Column(
        Integer,
        nullable=True,
        comment="Score final de qualidade OCR",
    )

    score_geometria = Column(
        Integer,
        nullable=True,
        comment="Score geométrico do memorial",
    )

    score_registral = Column(
        Integer,
        nullable=True,
        comment="Score registral/jurídico",
    )

    score_confianca = Column(
        Integer,
        nullable=True,
    )

    # =========================================================
    # CONTEÚDO OCR
    # =========================================================

    texto_extraido = Column(
        Text,
        nullable=True,
    )

    # =========================================================
    # JSON ESTRUTURADO OCR
    # =========================================================

    dados_extraidos_json = Column(
        JSONB,
        nullable=True,
    )

    # =========================================================
    # 🔥 NOVO — METADADOS COMPLETOS
    # =========================================================

    metadata_json = Column(
        JSONB,
        nullable=True,
        comment=(
            "Metadados técnicos da execução OCR"
        ),
    )

    # =========================================================
    # 🔥 NOVO — CONTROLE DE EXECUÇÃO
    # =========================================================

    modelo_llm = Column(
        String(120),
        nullable=True,
        comment="Modelo utilizado no OCR/LLM",
    )

    parser_utilizado = Column(
        String(120),
        nullable=True,
    )

    normalizador_utilizado = Column(
        String(120),
        nullable=True,
    )

    total_paginas = Column(
        Integer,
        nullable=True,
    )

    paginas_processadas = Column(
        Integer,
        nullable=True,
    )

    processado_em = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    possui_geojson = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    possui_memorial = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    possui_confrontantes = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    possui_historico = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    possui_documentos_pessoais = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    possui_dados_sigef = Column(
        Boolean     ,
        nullable=False,
        default=False,
    )

    possui_croqui = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    # =========================================================
    # 🔥 NOVO — LOGS TÉCNICOS
    # =========================================================

    warnings_json = Column(
        JSONB,
        nullable=True,
    )

    errors_json = Column(
        JSONB,
        nullable=True,
    )

    # =========================================================
    # 🔥 NOVO — TEMPO DE EXECUÇÃO
    # =========================================================

    started_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    finished_at = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    # =========================================================
    # ERRO FINAL
    # =========================================================

    erro = Column(
        Text,
        nullable=True,
    )

    # =========================================================
    # METADADOS TEMPORAIS
    # =========================================================

    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # =========================================================
    # RELACIONAMENTOS ORM
    # =========================================================

    document = relationship(
        "Document",
        lazy="joined",
    )

    ocr_prompt = relationship(
        "OcrPrompt",
        lazy="joined",
    )

    # =========================================================
    # REPRESENTAÇÃO
    # =========================================================

    def __repr__(self) -> str:
        return (
            f"<OcrResult "
            f"id={self.id} "
            f"document_id={self.document_id} "
            f"pipeline={self.pipeline_tipo} "
            f"status={self.status} "
            f"provider={self.provider}>"
        )