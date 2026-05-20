from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Boolean,
    JSON,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class DocumentoTecnico(Base):
    __tablename__ = "documentos_tecnicos"

    __table_args__ = (
        # Garante que não exista a mesma versão para o mesmo "grupo" (document_group_key) dentro do imóvel
        UniqueConstraint(
            "imovel_id",
            "document_group_key",
            "versao",
            name="uq_doc_tecnico_imovel_group_versao",
        ),
        Index("ix_doc_tecnico_imovel_group", "imovel_id", "document_group_key"),
        Index("ix_doc_tecnico_status", "status_tecnico"),
        Index("ix_doc_tecnico_pipeline", "pipeline_utilizado"),
        Index("ix_doc_tecnico_origem_ocr", "origem_ocr"),
        Index("ix_doc_tecnico_doc_origem", "documento_origem_id"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # =========================================================
    # 🔗 RELAÇÃO DIRETA COM IMÓVEL
    # =========================================================
    imovel_id = Column(
        Integer,
        ForeignKey("imoveis.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # =========================================================
    # IDENTIDADE DO DOCUMENTO (AGRUPAMENTO + VERSIONAMENTO)
    # =========================================================
    # Chave do grupo do documento dentro do imóvel.
    # Ex.: "MEMORIAL", "CROQUI", "PLANTA_SIGEF", "PLANILHA_SIGEF", "RELATORIO_SOBREPOSICAO"
    document_group_key = Column(String(80), nullable=False)

    # Versão incremental por document_group_key (começa em 1)
    versao = Column(Integer, nullable=False, default=1)

    # Marca a versão atual (ativa) do grupo
    is_versao_atual = Column(Boolean, nullable=False, default=True)

    gerado_automaticamente = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    # =========================================================
    # TIPO / STATUS TÉCNICO
    # =========================================================
    # Tipo humano do documento (ex.: "Memorial Descritivo", "Croqui", "Planilha SIGEF")
    tipo = Column(String(120), nullable=False)

    origem_ocr = Column(
        String(120),
        nullable=True,
        index=True,
    )

    prompt_utilizado = Column(
        String(255),
        nullable=True,
    )

    pipeline_utilizado = Column(
        String(255),
        nullable=True,
        index=True,
    )

    engine_utilizada = Column(
        String(120),
        nullable=True,
    )

    # Status técnico padronizado:
    # RASCUNHO | EM_ANALISE | APROVADO | CORRIGIR | REPROVADO
    status_tecnico = Column(String(30), nullable=False, default="RASCUNHO")

    # Observações técnicas (ex.: inconsistência detectada, ajuste de confrontantes etc.)
    observacoes_tecnicas = Column(Text, nullable=True)

    # =========================================================
    # CONTEÚDO / ARQUIVOS
    # =========================================================
    # Conteúdo textual (ex.: memorial em texto, logs, parecer)
    conteudo_texto = Column(Text, nullable=True)

    # Conteúdo estruturado (ex.: linhas do memorial, vertices, metadados SIGEF-ready)
    conteudo_json = Column(JSON, nullable=True)

    # Caminho/URL do arquivo gerado (PDF, SVG, CSV, ODS etc.)
    arquivo_path = Column(String(512), nullable=True)

    documento_origem_id = Column(
        Integer,
        ForeignKey(
            "documentos_tecnicos.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    # Metadados extras (ex.: hash, origem, versão do algoritmo, epsg, etc.)
    metadata_json = Column(JSON, nullable=True)

    outputs_gerados_json = Column(
        JSON,
        nullable=True,
    )

    # =========================================================
    # METADADOS TEMPORAIS
    # =========================================================
    gerado_em = Column(DateTime(timezone=True), nullable=True)

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

    processado_em = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    tempo_processamento_ms = Column(
        Integer,
        nullable=True,
    )

    score_confianca = Column(
        Integer,
        nullable=True,
    )

    # =========================================================
    # RELACIONAMENTOS
    # =========================================================
    imovel = relationship(
        "Imovel",
        lazy="joined",
        backref="documentos_tecnicos",
    )

    documento_origem = relationship(
        "DocumentoTecnico",
        remote_side=[id],
        lazy="joined",
    )

    def __repr__(self) -> str:
        return (
            f"<DocumentoTecnico "
            f"id={self.id} "
            f"imovel_id={self.imovel_id} "
            f"group={self.document_group_key} "
            f"versao={self.versao} "
            f"status={self.status_tecnico} "
            f"pipeline={self.pipeline_utilizado} "
            f"ocr={self.origem_ocr}>"
        )
