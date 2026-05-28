from datetime import datetime
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Float,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy import Boolean
from app.core.database import Base


class Imovel(Base):
    __tablename__ = "imoveis"

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "matricula_principal",
            name="uq_project_matricula_principal",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    # 🔗 Projeto ao qual o imóvel pertence
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 🔗 Município oficial (base VTI / VTN)
    municipio_id = Column(
        Integer,
        ForeignKey("municipios.id"),
        nullable=False,
        index=True,
    )

    documento_origem_id = Column(
        Integer,
        ForeignKey(
            "documents.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    responsavel_tecnico_id = Column(
        Integer,
        ForeignKey(
            "responsaveis_tecnicos.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    # ================================
    # IDENTIFICAÇÃO DO IMÓVEL
    # ================================

    nome = Column(String(255), nullable=True)
    status_tecnico = Column(
        String(50),
        nullable=True,
        index=True,
    )
    descricao = Column(Text, nullable=True)

    area_georreferenciada = Column(
        Float,
        nullable=True,
    )

    perimetro_georreferenciado = Column(
        Float,
        nullable=True,
    )

    possui_geometria_valida = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Área oficial do imóvel (hectares)
    area_hectares = Column(Float, nullable=False)

    score_confianca_ocr = Column(
        Integer,
        nullable=True,
    )

    validado_tecnicamente = Column(
        Boolean,
        nullable=False,
        default=False,
    )

    # Código CCIR (quando existir)
    ccir = Column(String(50), nullable=True)

    codigo_incra = Column(
        String(100),
        nullable=True,
    )

    nirf = Column(
        String(100),
        nullable=True,
    )

    itr = Column(
        String(100),
        nullable=True,
    )

    # Número da matrícula principal
    matricula_principal = Column(String(100), nullable=True)

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

    project = relationship(
        "Project",
        back_populates="imoveis",
        lazy="joined",
    )

    municipio = relationship(
        "Municipio",
        lazy="joined",
    )

    documento_origem = relationship(
        "Document",
        lazy="joined",
    )

    responsavel_tecnico = relationship(
        "ResponsavelTecnico",
        lazy="joined",
    )

    confrontantes = relationship(
        "Confrontante",
        back_populates="imovel",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    geometrias = relationship(
        "Geometria",
        back_populates="imovel",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    matriculas = relationship(
        "Matricula",
        back_populates="imovel",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    proprietarios = relationship(
        "Proprietario",
        back_populates="imovel",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    documentos_tecnicos = relationship(
        "DocumentoTecnico",
        back_populates="imovel",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return (
            f"<Imovel "
            f"id={self.id} "
            f"project_id={self.project_id} "
            f"area={self.area_hectares}ha "
            f"pipeline={self.pipeline_utilizado} "
            f"ocr={self.origem_ocr}>"
        )
