from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Integer,
    JSON,
    String,
    Text,
    Index,
)

from app.core.database import Base


class OcrPrompt(Base):
    __tablename__ = "ocr_prompts"

    __table_args__ = (
        Index("ix_ocr_prompt_categoria", "categoria"),
        Index("ix_ocr_prompt_pipeline", "pipeline"),
        Index("ix_ocr_prompt_engine", "engine"),
        Index("ix_ocr_prompt_ativo", "ativo"),
        Index("ix_ocr_prompt_slug", "slug"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # =========================================================
    # IDENTIFICAÇÃO
    # =========================================================

    nome = Column(
        String(255),
        nullable=False,
    )

    slug = Column(
        String(120),
        nullable=False,
        unique=True,
        index=True,
    )

    categoria = Column(
        String(100),
        nullable=False,
        index=True,
    )

    descricao = Column(
        Text,
        nullable=True,
    )

    # =========================================================
    # PIPELINE OCR
    # =========================================================

    # MATRÍCULA
    # DOCUMENTO_PESSOAL
    # FICHA_SIG
    # CROQUI
    # MEMORIAL
    # DADOS_BRUTOS
    # REGISTRAL
    # CONFRONTANTES
    # GEOMETRIA
    pipeline = Column(
        String(100),
        nullable=False,
        index=True,
    )

    # =========================================================
    # ENGINE / PROVIDER
    # =========================================================

    # GOOGLE_VISION
    # OPENAI
    # HIBRIDO
    engine = Column(
        String(80),
        nullable=False,
        default="GOOGLE",
        index=True,
    )

    # =========================================================
    # PROMPT BASE
    # =========================================================

    prompt = Column(
        Text,
        nullable=False,
    )

    # =========================================================
    # CONFIGURAÇÃO TÉCNICA
    # =========================================================

    versao = Column(
        Integer,
        nullable=False,
        default=1,
    )

    prioridade = Column(
        Integer,
        nullable=False,
        default=1,
    )

    timeout_execucao_segundos = Column(
        Integer,
        nullable=False,
        default=300,
    )

    max_tokens_llm = Column(
        Integer,
        nullable=True,
    )

    temperatura = Column(
        String(20),
        nullable=True,
    )

    modelo_llm = Column(
        String(120),
        nullable=True,
    )

    usar_google_vision = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    usar_openai = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    usar_pipeline_hibrido = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    idioma = Column(
        String(20),
        nullable=True,
        default="pt-BR",
    )

    # =========================================================
    # PARSER / NORMALIZAÇÃO
    # =========================================================

    parser_service = Column(
        String(255),
        nullable=True,
    )

    normalizer_service = Column(
        String(255),
        nullable=True,
    )

    post_processor_service = Column(
        String(255),
        nullable=True,
    )

    pipeline_executor = Column(
        String(255),
        nullable=True,
    )

    output_schema = Column(
        String(255),
        nullable=True,
    )

    # =========================================================
    # FLAGS FUNCIONAIS
    # =========================================================

    ativo = Column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
    )

    exige_geometria = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    exige_memorial = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    exige_confrontantes = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    exige_historico_registral = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    exige_proprietarios = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    exige_documentos_pessoais = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    gera_documento_tecnico = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    gera_geojson = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    gera_croqui = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    gera_memorial = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    gera_pdf = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    gera_docx = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    gera_dxf = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    gera_shp = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    gera_sigef = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    gera_txt = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    gera_csv = Column(
        Boolean,
        nullable=False,
        default=False,
    )


    persistir_banco = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    habilitar_validacao_semantica = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    habilitar_pos_processamento = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    habilitar_pipeline_registral = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    habilitar_pipeline_geometrico = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    habilitar_pipeline_confrontantes = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    # =========================================================
    # CONFIGURAÇÃO JSON DINÂMICA
    # =========================================================

    configuracao_json = Column(
        JSON,
        nullable=True,
    )

    schema_json = Column(
        JSON,
        nullable=True,
    )

    output_mapping_json = Column(
        JSON,
        nullable=True,
    )

    metadados_json = Column(
        JSON,
        nullable=True,
    )

    # =========================================================
    # FRONTEND / UX
    # =========================================================

    cor = Column(
        String(30),
        nullable=True,
    )

    icone = Column(
        String(80),
        nullable=True,
    )

    ordem_exibicao = Column(
        Integer,
        nullable=False,
        default=0,
    )

    exibir_frontend = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    # =========================================================
    # AUDITORIA
    # =========================================================

    observacoes = Column(
        Text,
        nullable=True,
    )

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

    def __repr__(self) -> str:
        return (
            f"<OcrPrompt "
            f"id={self.id} "
            f"slug={self.slug} "
            f"pipeline={self.pipeline} "
            f"engine={self.engine} "
            f"versao={self.versao} "
            f"ativo={self.ativo}>"
        )