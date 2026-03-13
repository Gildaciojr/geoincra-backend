from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    DateTime,
    String,
    ForeignKey,
    Text,
    Index,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class VisitaTecnica(Base):
    __tablename__ = "visitas_tecnicas"

    __table_args__ = (
        Index("ix_visita_project", "project_id"),
        Index("ix_visita_profissional", "profissional_id"),
        Index("ix_visita_data", "data_agendada"),
    )

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    profissional_id = Column(
        Integer,
        ForeignKey("profissionais.id", ondelete="CASCADE"),
        nullable=False,
    )

    data_agendada = Column(
        DateTime,
        nullable=False,
    )

    status = Column(
        String(30),
        nullable=False,
        default="PENDENTE",
    )

    observacoes = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    project = relationship("Project", lazy="joined")
    profissional = relationship("Profissional", lazy="joined")

    def __repr__(self) -> str:
        return (
            f"<VisitaTecnica project_id={self.project_id} "
            f"profissional_id={self.profissional_id} "
            f"data={self.data_agendada}>"
        )