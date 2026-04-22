from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ProfissionalResumoResponse(BaseModel):
    id: int
    nome_completo: str
    tipo_pessoa: Optional[str] = None
    cpf: Optional[str] = None
    cnpj: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None

    class Config:
        from_attributes = True


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
    observacoes: Optional[str] = None
    created_at: datetime

    # 🔥 NOVO — permite retornar o profissional vinculado já resolvido pelo ORM
    profissional: Optional[ProfissionalResumoResponse] = None

    class Config:
        from_attributes = True