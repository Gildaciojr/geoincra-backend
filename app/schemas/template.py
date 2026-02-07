from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class TemplateBase(BaseModel):
    nome: str
    descricao: Optional[str] = None
    categoria: str
    versao: Optional[str] = None


class TemplateCreate(TemplateBase):
    stored_filename: str
    original_filename: str
    file_path: str


class TemplateResponse(TemplateBase):
    id: int
    stored_filename: str
    original_filename: str
    ativo: bool
    created_at: datetime

    class Config:
        from_attributes = True
