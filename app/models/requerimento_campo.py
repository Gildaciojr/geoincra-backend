# app/models/requerimento_campo.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class RequerimentoCampo(Base):
    __tablename__ = "requerimento_campos"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    tipo = Column(String(80), nullable=False)  # ex: "AVERBACAO_R09"
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=True)

    dados_json = Column(JSONB, nullable=False, default=dict)

    status = Column(String(30), nullable=False, default="RASCUNHO")

    created_at = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)

    project = relationship("Project", lazy="select")
