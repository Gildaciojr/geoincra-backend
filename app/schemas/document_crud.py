from sqlalchemy.orm import Session
from app.models.document import Document
from app.schemas.document import DocumentCreate

def create_document(db: Session, project_id: int, data: DocumentCreate):
    doc = Document(
        project_id=project_id,
        doc_type=data.doc_type,
        description=data.description,
        stored_filename=data.stored_filename,
        original_filename=data.original_filename,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc

def get_document(db: Session, document_id: int):
    return db.query(Document).filter(Document.id == document_id).first()

def list_documents_by_project(db: Session, project_id: int):
    return db.query(Document).filter(Document.project_id == project_id).all()

def delete_document(db: Session, document_id: int):
    doc = get_document(db, document_id)
    if doc:
        db.delete(doc)
        db.commit()
    return doc
