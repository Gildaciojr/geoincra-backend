from datetime import datetime
from pydantic import BaseModel, Field


class DocumentBase(BaseModel):
    doc_type: str = Field(
        ...,
        min_length=2,
        max_length=50,
    )

    stored_filename: str = Field(
        ...,
        min_length=1,
        max_length=255,
    )
    original_filename: str | None = Field(
    default=None,
    max_length=255,
    )
    content_type: str | None = Field(
    default=None,
    max_length=100,
    )
    description: str | None = None
    file_path: str | None = Field(
    default=None,
    max_length=512,
    )
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
