from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Boolean,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class ProjetoProfissional(Base):
    __tablename__ = "projetos_profissionais"

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "ativo",
            name="uq_projeto_profissional_ativo",
        ),
        Index("ix_proj_prof_status", "status_execucao"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # =========================================================
    # RELAÇÕES
    # =========================================================

    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    profissional_id = Column(
        Integer,
        ForeignKey("profissionais.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    proposta_profissional_id = Column(
        Integer,
        ForeignKey("propostas_profissionais.id", ondelete="SET NULL"),
        nullable=True,
    )

    # =========================================================
    # STATUS DE EXECUÇÃO
    # =========================================================
    # CONVIDADO | ACEITO | EM_EXECUCAO | PAUSADO | FINALIZADO | CANCELADO
    status_execucao = Column(
        String(40),
        nullable=False,
        default="ACEITO",
    )

    ativo = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    iniciado_em = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    finalizado_em = Column(
        DateTime(timezone=True),
        nullable=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # =========================================================
    # RELACIONAMENTOS
    # =========================================================

    project = relationship(
        "Project",
        backref="profissional_ativo",
        lazy="joined",
    )

    profissional = relationship(
        "Profissional",
        backref="projetos_execucao",
        lazy="joined",
    )

    proposta = relationship(
        "PropostaProfissional",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return (
            f"<ProjetoProfissional project_id={self.project_id} "
            f"profissional_id={self.profissional_id} "
            f"status={self.status_execucao} ativo={self.ativo}>"
        )
