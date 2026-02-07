from sqlalchemy.orm import Session

from app.models.document import Document
from app.schemas.document import DocumentCreate


def create_document(db: Session, project_id: int, data: DocumentCreate) -> Document:
    doc = Document(
        project_id=project_id,
        matricula_id=data.matricula_id,
        doc_type=data.doc_type,
        stored_filename=data.stored_filename,
        original_filename=data.original_filename,
        content_type=data.content_type,
        description=data.description,
        file_path=data.file_path,
        observacoes=data.observacoes,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def get_document(db: Session, document_id: int) -> Document | None:
    return db.query(Document).filter(Document.id == document_id).first()


def list_documents_by_project(db: Session, project_id: int) -> list[Document]:
    return (
        db.query(Document)
        .filter(Document.project_id == project_id)
        .order_by(Document.uploaded_at.desc())
        .all()
    )


def delete_document(db: Session, document_id: int) -> bool:
    doc = get_document(db, document_id)
    if not doc:
        return False
    db.delete(doc)
    db.commit()
    return True
