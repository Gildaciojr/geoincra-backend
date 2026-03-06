from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.ocr_result import OcrResult
from app.models.document import Document

from app.crud.automation_job_crud import create_ocr_job


class OcrService:

    @staticmethod
    def iniciar_ocr(
        db: Session,
        document_id: int,
        user_id: int,
        prompt_id: int,
        provider: str = "GOOGLE",
    ) -> OcrResult:

        # ------------------------------------------------
        # VALIDAR DOCUMENTO
        # ------------------------------------------------
        doc = db.query(Document).filter(Document.id == document_id).first()

        if not doc:
            raise HTTPException(status_code=404, detail="Documento não encontrado.")

        # ------------------------------------------------
        # CRIAR REGISTRO OCR
        # ------------------------------------------------
        ocr = OcrResult(
            document_id=document_id,
            status="PENDING",
            provider=provider,
        )

        db.add(ocr)
        db.commit()
        db.refresh(ocr)

        # ------------------------------------------------
        # CRIAR JOB PARA WORKER
        # ------------------------------------------------
        create_ocr_job(
            db=db,
            user_id=user_id,
            project_id=doc.project_id,
            document_id=document_id,
            prompt_id=prompt_id,
        )

        return ocr