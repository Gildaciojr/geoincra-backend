from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from app.core.database import Base


class ExternalCredential(Base):
    __tablename__ = "external_credentials"

    id = Column(UUID(as_uuid=True), primary_key=True)
    user_id = Column(Integer, nullable=False)

    provider = Column(String(50), nullable=False)  # RI_DIGITAL
    login = Column(String(255), nullable=False)
    password_encrypted = Column(String, nullable=False)

    active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now())
