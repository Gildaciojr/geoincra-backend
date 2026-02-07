from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.ocr_result import OcrResult
from app.models.document import Document


class OcrService:
    @staticmethod
    def iniciar_ocr(
        db: Session,
        document_id: int,
        provider: str = "NONE",
    ) -> OcrResult:
        doc = db.query(Document).filter(Document.id == document_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="Documento não encontrado.")

        ocr = OcrResult(
            document_id=document_id,
            status="PENDING",
            provider=provider,
        )

        db.add(ocr)
        db.commit()
        db.refresh(ocr)

        return ocr
