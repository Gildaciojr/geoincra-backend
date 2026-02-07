from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user_required
from app.models.user import User
from app.models.project import Project
from app.schemas.document import DocumentCreate, DocumentResponse
from app.crud.document_crud import (
    create_document,
    list_documents_by_project,
    get_document,
    delete_document,
)

router = APIRouter()


def _check_project_owner(db: Session, project_id: int, user_id: int):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == user_id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    return project


@router.get("/documents", response_model=list[DocumentResponse])
def list_docs_by_query(
    project_id: int = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    _check_project_owner(db, project_id, current_user.id)
    return list_documents_by_project(db, project_id)


@router.get("/documents/{document_id}", response_model=DocumentResponse)
def get_doc_route(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    doc = get_document(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")

    _check_project_owner(db, doc.project_id, current_user.id)
    return doc


@router.post("/projects/{project_id}/documents", response_model=DocumentResponse)
def create_document_route(
    project_id: int,
    payload: DocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    _check_project_owner(db, project_id, current_user.id)
    return create_document(db, project_id, payload)


@router.get("/projects/{project_id}/documents", response_model=list[DocumentResponse])
def list_docs_route(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    _check_project_owner(db, project_id, current_user.id)
    return list_documents_by_project(db, project_id)


@router.delete("/documents/{document_id}")
def delete_doc_route(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    doc = get_document(db, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado.")

    _check_project_owner(db, doc.project_id, current_user.id)
    delete_document(db, document_id)
    return {"status": "deleted", "id": document_id}
