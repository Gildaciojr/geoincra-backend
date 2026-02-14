from sqlalchemy import Column, Integer, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func

from app.core.database import Base


class AutomationJob(Base):
    __tablename__ = "automation_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True)
    user_id = Column(Integer, nullable=False)
    project_id = Column(Integer)

    type = Column(Text, nullable=False)
    status = Column(Text, nullable=False)

    payload_json = Column(JSONB, nullable=False)
    error_message = Column(Text)

    started_at = Column(DateTime(timezone=True))
    finished_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
