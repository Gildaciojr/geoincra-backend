from sqlalchemy import Column, Date, DateTime, String, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.core.database import Base


class AutomationResult(Base):
    __tablename__ = "automation_results"

    id = Column(UUID(as_uuid=True), primary_key=True)
    job_id = Column(UUID(as_uuid=True), nullable=False)

    protocolo = Column(String(50))
    matricula = Column(String(50))
    cnm = Column(String(50))
    cartorio = Column(String(255))
    data_pedido = Column(Date)

    file_path = Column(Text, nullable=False)
    metadata_json = Column(JSONB)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
