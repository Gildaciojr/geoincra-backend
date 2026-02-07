from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class CalculationParameterBase(BaseModel):
    nome: str
    descricao: Optional[str] = None
    valor: float
    unidade: Optional[str] = None
    categoria: Optional[str] = None
    ativo: bool = True


class CalculationParameterCreate(CalculationParameterBase):
    pass


class CalculationParameterUpdate(BaseModel):
    nome: Optional[str] = None
    descricao: Optional[str] = None
    valor: Optional[float] = None
    unidade: Optional[str] = None
    categoria: Optional[str] = None
    ativo: Optional[bool] = None


class CalculationParameterRead(CalculationParameterBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
