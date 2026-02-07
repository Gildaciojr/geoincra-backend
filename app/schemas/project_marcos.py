from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class MarcoMotivo(BaseModel):
    codigo: str = Field(..., min_length=2, max_length=80)
    descricao: str = Field(..., min_length=2, max_length=500)


class MarcoAvaliacaoResponse(BaseModel):
    project_id: int

    pode_avancar: bool
    status_atual: Optional[str] = None
    status_sugerido: Optional[str] = None
    descricao: Optional[str] = None

    gerado_em: datetime
    motivos: List[MarcoMotivo] = Field(default_factory=list)


class MarcoAplicarResponse(BaseModel):
    project_id: int
    aplicado: bool
    status_aplicado: Optional[str] = None

    gerado_em: datetime
    motivos: List[MarcoMotivo] = Field(default_factory=list)
