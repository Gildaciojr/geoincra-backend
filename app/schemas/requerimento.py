# app/schemas/requerimento.py
from datetime import datetime
from pydantic import BaseModel, Field
from typing import Any


class RequerimentoUpsert(BaseModel):
    tipo: str = Field(..., max_length=80)
    template_id: int | None = None
    status: str | None = "RASCUNHO"
    dados_json: dict[str, Any] = Field(default_factory=dict)


class RequerimentoOut(BaseModel):
    id: int
    project_id: int
    tipo: str
    template_id: int | None
    status: str
    dados_json: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
