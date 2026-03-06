from sqlalchemy.orm import Session
from app.models.ocr_prompt import OcrPrompt


def list_active_prompts(db: Session):
    return (
        db.query(OcrPrompt)
        .filter(OcrPrompt.ativo == True)
        .order_by(OcrPrompt.nome.asc())
        .all()
    )