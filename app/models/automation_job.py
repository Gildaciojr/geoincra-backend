# geoincra_backend/app/models/automation_job.py
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from sqlalchemy.types import Enum as SAEnum

from app.core.database import Base

# IMPORTANTÍSSIMO:
# - O enum JÁ EXISTE no Postgres
# - create_type=False impede SQLAlchemy de tentar recriar
AutomationTypeEnum = SAEnum(
    "RI_DIGITAL_MATRICULA",
    "ONR_SIGRI_CONSULTA",
    name="automation_type",
    native_enum=True,
    create_type=False,
)

AutomationStatusEnum = SAEnum(
    "PENDING",
    "PROCESSING",
    "COMPLETED",
    "FAILED",
    name="automation_status",
    native_enum=True,
    create_type=False,
)


class AutomationJob(Base):
    __tablename__ = "automation_jobs"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()"),
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )

    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )

    type = Column(AutomationTypeEnum, nullable=False)

    status = Column(
        AutomationStatusEnum,
        nullable=False,
        server_default=text("'PENDING'::automation_status"),
    )

    payload_json = Column(JSONB, nullable=False)

    # ✅ CORRETO: Text aceita NULL sem gambiarra
    error_message = Column(Text, nullable=True)

    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
