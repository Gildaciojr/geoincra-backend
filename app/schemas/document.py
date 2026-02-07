from datetime import datetime
from pydantic import BaseModel


class DocumentBase(BaseModel):
    doc_type: str
    stored_filename: str
    original_filename: str | None = None
    content_type: str | None = None
    description: str | None = None
    file_path: str | None = None
    observacoes: str | None = None
    matricula_id: int | None = None


class DocumentCreate(DocumentBase):
    pass


class DocumentResponse(DocumentBase):
    id: int
    project_id: int
    uploaded_at: datetime

    class Config:
        from_attributes = True
