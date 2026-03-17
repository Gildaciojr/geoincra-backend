from sqlalchemy import Column, Date, DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.sql import func

from app.core.database import Base


class AutomationResult(Base):
    __tablename__ = "automation_results"

    id = Column(
      UUID(as_uuid=True),
      primary_key=True,
      server_default=text("gen_random_uuid()"),
    )

    job_id = Column(
      UUID(as_uuid=True),
      ForeignKey("automation_jobs.id", ondelete="CASCADE"),
      nullable=False,
    )

    protocolo = Column(String(50), nullable=True)
    matricula = Column(String(50), nullable=True)
    cnm = Column(String(50), nullable=True)
    cartorio = Column(String(255), nullable=True)
    data_pedido = Column(Date, nullable=True)

    file_path = Column(Text, nullable=True)
    metadata_json = Column(JSONB, nullable=True)

    created_at = Column(
      DateTime(timezone=True),
      nullable=False,
      server_default=func.now(),
    )