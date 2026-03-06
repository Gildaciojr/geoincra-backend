from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime
from app.core.database import Base


class OcrPrompt(Base):
    __tablename__ = "ocr_prompts"

    id = Column(Integer, primary_key=True, index=True)

    nome = Column(String(255), nullable=False)
    categoria = Column(String(100), nullable=False)

    prompt = Column(Text, nullable=False)

    ativo = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow)