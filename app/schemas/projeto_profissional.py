from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ProjetoProfissionalBase(BaseModel):
    profissional_id: int = Field(..., ge=1)
    proposta_profissional_id: Optional[int] = None


class ProjetoProfissionalCreate(ProjetoProfissionalBase):
    pass


class ProjetoProfissionalUpdate(BaseModel):
    status_execucao: Optional[str] = Field(
        default=None,
        description="CONVIDADO | ACEITO | EM_EXECUCAO | PAUSADO | FINALIZADO | CANCELADO",
    )

    ativo: Optional[bool] = None
    finalizado_em: Optional[datetime] = None


class ProjetoProfissionalResponse(ProjetoProfissionalBase):
    id: int
    project_id: int
    status_execucao: str
    ativo: bool
    iniciado_em: datetime
    finalizado_em: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True
