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

    # ================================
    # IDENTIFICAÇÃO DO IMÓVEL
    # ================================

    nome = Column(String(255), nullable=True)
    descricao = Column(Text, nullable=True)

    # Área oficial do imóvel (hectares)
    area_hectares = Column(Float, nullable=False)

    # Código CCIR (quando existir)
    ccir = Column(String(50), nullable=True)

    # Número da matrícula principal
    matricula_principal = Column(String(100), nullable=True)

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

    def __repr__(self) -> str:
        return (
            f"<Imovel id={self.id} "
            f"area={self.area_hectares}ha "
            f"project_id={self.project_id}>"
        )
