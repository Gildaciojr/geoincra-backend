from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class AutomacaoMotivo(BaseModel):
    codigo: str = Field(..., min_length=2, max_length=80)
    descricao: str = Field(..., min_length=2, max_length=500)


class AutomacaoStatusDiagnostico(BaseModel):
    project_id: int
    status_sugerido: str = Field(..., min_length=2, max_length=60)
    descricao_status: str = Field(..., min_length=2, max_length=800)

    bloqueado: bool
    bloqueio_motivo: Optional[str] = None

    gerado_em: datetime

    motivos: List[AutomacaoMotivo] = Field(default_factory=list)


class AutomacaoAplicarResponse(BaseModel):
    project_id: int
    status_aplicado: str = Field(..., min_length=2, max_length=60)
    criado_novo_status: bool

    gerado_em: datetime

    motivos: List[AutomacaoMotivo] = Field(default_factory=list)
