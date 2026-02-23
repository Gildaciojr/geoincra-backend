# geoincra_backend/app/models/automation_result.py
from sqlalchemy import Column, Date, DateTime, String, Text, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.core.database import Base


class AutomationResult(Base):
    __tablename__ = "automation_results"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    job_id = Column(UUID(as_uuid=True), ForeignKey("automation_jobs.id", ondelete="CASCADE"), nullable=False)

    # Campos “genéricos” (RI Digital usa alguns)
    protocolo = Column(String(50), nullable=True)
    matricula = Column(String(50), nullable=True)
    cnm = Column(String(50), nullable=True)
    cartorio = Column(String(255), nullable=True)
    data_pedido = Column(Date, nullable=True)

    # Arquivo principal salvo (PDF RI Digital / KMZ ONR)
    file_path = Column(Text, nullable=True)

    # ONR/SIG-RI: dados oficiais do modal aqui
    metadata_json = Column(JSONB, nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
