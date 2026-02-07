from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class ParcelaPagamentoBase(BaseModel):
    numero: int = Field(..., ge=1)
    percentual: float = Field(..., gt=0, le=100)
    valor: float = Field(..., gt=0)

    vencimento: Optional[datetime] = None

    status: str = Field(default="PENDENTE", min_length=1, max_length=20)

    pago_em: Optional[datetime] = None
    forma_pagamento: Optional[str] = Field(default=None, max_length=50)
    referencia_interna: Optional[str] = Field(default=None, max_length=120)
    observacoes: Optional[str] = Field(default=None, max_length=512)


class ParcelaPagamentoCreate(ParcelaPagamentoBase):
    pass


class ParcelaPagamentoUpdate(BaseModel):
    vencimento: Optional[datetime] = None
    status: Optional[str] = Field(default=None, min_length=1, max_length=20)

    pago_em: Optional[datetime] = None
    forma_pagamento: Optional[str] = Field(default=None, max_length=50)
    referencia_interna: Optional[str] = Field(default=None, max_length=120)
    observacoes: Optional[str] = Field(default=None, max_length=512)


class ParcelaPagamentoResponse(ParcelaPagamentoBase):
    id: int
    pagamento_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class MarcarParcelaPagaRequest(BaseModel):
    forma_pagamento: Optional[str] = Field(default=None, max_length=50)
    observacoes: Optional[str] = Field(default=None, max_length=512)
    pago_em: Optional[datetime] = None
