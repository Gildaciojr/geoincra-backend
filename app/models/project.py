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

    # Tipo de processo (ex: GEOREFERENCIAMENTO, USUCAPIÃO, DESMEMBRAMENTO)
    tipo_processo = Column(String(80), nullable=True)

    # Município/UF apenas para referência rápida
    municipio = Column(String(120), nullable=True)
    uf = Column(String(2), nullable=True)

    # Códigos institucionais
    codigo_imovel_rural = Column(String(50), nullable=True)   # CCIR
    codigo_sncr = Column(String(50), nullable=True)
    codigo_car = Column(String(50), nullable=True)
    codigo_sigef = Column(String(50), nullable=True)

    observacoes = Column(Text, nullable=True)

    # Status do processo
    status = Column(
        String(50),
        nullable=False,
        default="rascunho",  # rascunho | em_andamento | finalizado | arquivado
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
        return f"<Project id={self.id} name={self.name} status={self.status}>"
