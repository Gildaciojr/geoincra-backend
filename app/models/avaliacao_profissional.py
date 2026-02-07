from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    Text,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class AvaliacaoProfissional(Base):
    __tablename__ = "avaliacoes_profissionais"

    __table_args__ = (
        Index("ix_avaliacao_profissional_profissional", "profissional_id"),
        Index("ix_avaliacao_profissional_project", "project_id"),
    )

    id = Column(Integer, primary_key=True, index=True)

    profissional_id = Column(
        Integer,
        ForeignKey("profissionais.id", ondelete="CASCADE"),
        nullable=False,
    )

    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    nota = Column(Float, nullable=False)
    comentario = Column(Text, nullable=True)

    origem = Column(
        String(50),
        nullable=False,
        default="INTERNA",
    )

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)

    profissional = relationship(
        "Profissional",
        back_populates="avaliacoes",
        lazy="joined",
    )

    project = relationship("Project", lazy="joined")

    def __repr__(self) -> str:
        return f"<AvaliacaoProfissional id={self.id} nota={self.nota}>"
