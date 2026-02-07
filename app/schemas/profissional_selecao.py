# app/schemas/profissional_selecao.py

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class ProfissionalSelecaoBase(BaseModel):
    score: float = Field(default=0.0, ge=0.0)
    criterios_json: Optional[Dict[str, Any]] = None
    automatico: bool = True
    observacoes: Optional[str] = None
    escolhido_em: Optional[datetime] = None
    is_atual: bool = True


class ProfissionalSelecaoCreate(BaseModel):
    observacoes: Optional[str] = None


class ProfissionalSelecaoManualCreate(BaseModel):
    profissional_id: int = Field(..., ge=1)
    observacoes: Optional[str] = None


class ProfissionalSelecaoResponse(ProfissionalSelecaoBase):
    id: int
    project_id: int
    profissional_id: int
    escolhido_por_user_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True
