from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class OcrResult(Base):
    __tablename__ = "ocr_results"

    id = Column(Integer, primary_key=True, index=True)

    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status = Column(
        String(30),
        nullable=False,
        default="PENDING",  # PENDING | PROCESSING | DONE | ERROR
    )

    provider = Column(
        String(50),
        nullable=False,
        default="NONE",  # AWS_TEXTRACT | GOOGLE | AZURE | NONE
    )

    texto_extraido = Column(Text, nullable=True)
    dados_extraidos_json = Column(Text, nullable=True)

    erro = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    document = relationship("Document", lazy="joined")
