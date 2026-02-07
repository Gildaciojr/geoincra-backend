# app/models/profissional_selecao.py

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Float,
    Boolean,
    Text,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class ProfissionalSelecao(Base):
    __tablename__ = "profissionais_selecoes"

    __table_args__ = (
        Index("ix_prof_sel_project_atual", "project_id", "is_atual"),
        Index("ix_prof_sel_profissional", "profissional_id"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # =========================================================
    # 🔗 RELAÇÕES
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

    escolhido_por_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # =========================================================
    # DADOS DA ESCOLHA
    # =========================================================
    score = Column(Float, nullable=False, default=0.0)

    # Auditoria completa do processo (ranking, critérios, etc.)
    criterios_json = Column(JSON, nullable=True)

    automatico = Column(Boolean, nullable=False, default=True)

    observacoes = Column(Text, nullable=True)

    escolhido_em = Column(DateTime(timezone=True), nullable=False, default=datetime.utcnow)

    # Marca a seleção atual do projeto (mantemos histórico)
    is_atual = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    # =========================================================
    # RELACIONAMENTOS ORM
    # =========================================================
    project = relationship("Project", lazy="joined")
    profissional = relationship("Profissional", lazy="joined")
    escolhido_por = relationship("User", lazy="joined")

    def __repr__(self) -> str:
        return (
            f"<ProfissionalSelecao id={self.id} project_id={self.project_id} "
            f"profissional_id={self.profissional_id} score={self.score} atual={self.is_atual}>"
        )
