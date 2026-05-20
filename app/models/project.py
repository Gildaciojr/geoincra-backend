from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)

    # Identificação do processo
    name = Column(String(255), nullable=False)
    descricao_simplificada = Column(String(512), nullable=True)

    outputs_gerados_json = Column(
        Text,
        nullable=True,
    )

    # Tipo de processo (ex: GEOREFERENCIAMENTO, USUCAPIÃO, DESMEMBRAMENTO)
    tipo_processo = Column(String(80), nullable=True)
    etapa_pipeline = Column(
        String(120),
        nullable=True,
    )

    # Município/UF apenas para referência rápida
    municipio = Column(String(120), nullable=True)
    uf = Column(String(2), nullable=True)

    # Códigos institucionais
    codigo_imovel_rural = Column(String(50), nullable=True)   # CCIR
    codigo_sncr = Column(String(50), nullable=True)
    codigo_car = Column(String(50), nullable=True)
    codigo_sigef = Column(String(50), nullable=True)

    origem_ocr = Column(
        String(120),
        nullable=True,
        index=True,
    )

    prompt_principal_utilizado = Column(
        String(255),
        nullable=True,
    )

    pipeline_principal = Column(
        String(255),
        nullable=True,
        index=True,
    )

    engine_ocr_utilizada = Column(
        String(120),
        nullable=True,
    )

    observacoes = Column(Text, nullable=True)

    score_confianca_ocr = Column(
        Integer,
        nullable=True,
    )

    status_tecnico = Column(
        String(50),
        nullable=True,
        index=True,
    )

    possui_geometria_valida = Column(
        Integer,
        nullable=False,
        default=0,
    )

    possui_memorial = Column(
        Integer,
        nullable=False,
        default=0,
    )

    possui_sigef = Column(
        Integer,
        nullable=False,
        default=0,
    )

    # Status do processo
    status = Column(
        String(50),
        nullable=False,
        default="rascunho",  # rascunho | em_andamento | finalizado | arquivado
    )

    status_processamento = Column(
        String(50),
        nullable=True,
        index=True,
    )

    processado_em = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Proprietário do processo (usuário do sistema)
    owner_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
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

    # ================================
    # RELACIONAMENTOS
    # ================================

    owner = relationship(
        "User",
        back_populates="projects",
        lazy="joined",
    )

    imoveis = relationship(
        "Imovel",
        back_populates="project",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    documents = relationship(
        "Document",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    timeline_entries = relationship(
        "TimelineEntry",
        back_populates="project",
        cascade="all, delete-orphan",
    )

    proposals = relationship(
        "Proposal",
        back_populates="project",
        cascade="all, delete-orphan",
        lazy="select",
    )



    def __repr__(self) -> str:
        return (
            f"<Project "
            f"id={self.id} "
            f"name={self.name} "
            f"status={self.status} "
            f"pipeline={self.pipeline_principal} "
            f"ocr={self.origem_ocr}>"
        )
