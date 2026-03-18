from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class VisitaTecnicaCreate(BaseModel):
    data_agendada: datetime
    observacoes: Optional[str] = None


class VisitaTecnicaUpdate(BaseModel):
    status: Optional[str] = Field(
        default=None,
        description="PENDENTE | CONFIRMADA | REALIZADA | CANCELADA",
    )

    observacoes: Optional[str] = None


class VisitaTecnicaResponse(BaseModel):
    id: int
    project_id: int
    profissional_id: int
    data_agendada: datetime
    status: str
    observacoes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True