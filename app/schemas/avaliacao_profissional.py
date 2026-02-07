from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AvaliacaoProfissionalBase(BaseModel):
    nota: float = Field(..., ge=1.0, le=5.0)
    comentario: Optional[str] = None


class AvaliacaoProfissionalCreate(AvaliacaoProfissionalBase):
    profissional_id: int


class AvaliacaoProfissionalResponse(AvaliacaoProfissionalBase):
    id: int
    project_id: int
    profissional_id: int
    created_at: datetime

    class Config:
        from_attributes = True
