from sqlalchemy.orm import Session
from app.models.ocr_result import OcrResult


def get_ocr_result(db: Session, ocr_id: int):
    return db.query(OcrResult).filter(OcrResult.id == ocr_id).first()


def list_ocr_by_document(db: Session, document_id: int):
    return (
        db.query(OcrResult)
        .filter(OcrResult.document_id == document_id)
        .order_by(OcrResult.created_at.desc())
        .all()
    )
