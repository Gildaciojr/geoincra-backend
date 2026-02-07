from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.project import Project
from app.schemas.ocr import OcrRequest, OcrResponse
from app.services.ocr_service import OcrService
from app.crud.ocr_crud import get_ocr_result, list_ocr_by_document
from app.crud.document_crud import get_document

router = APIRouter()


def _check_project_owner(db: Session, project_id: int, user_id: int):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == user_id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    return project


@router.post("/ocr", response_model=OcrResponse)
def iniciar_ocr(
    payload: OcrRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = get_document(db, payload.document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")

    _check_project_owner(db, doc.project_id, current_user.id)

    return OcrService.iniciar_ocr(
        db=db,
        document_id=payload.document_id,
        provider=payload.provider,
    )


@router.get("/ocr/{ocr_id}", response_model=OcrResponse)
def get_ocr(
    ocr_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    obj = get_ocr_result(db, ocr_id)
    if not obj:
        raise HTTPException(status_code=404, detail="OCR não encontrado.")

    _check_project_owner(db, obj.document.project_id, current_user.id)
    return obj


@router.get("/documents/{document_id}/ocr", response_model=list[OcrResponse])
def list_ocr_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc = get_document(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")

    _check_project_owner(db, doc.project_id, current_user.id)
    return list_ocr_by_document(db, document_id)
