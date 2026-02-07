from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# =========================================================
# BASE
# =========================================================
class PagamentoBase(BaseModel):
    descricao: str = Field(..., min_length=3, max_length=255)
    valor: float = Field(..., gt=0)

    modelo: str = Field(
        default="100",
        description="Modelos financeiros: 100 | 50_50 | 20_30_50 | CUSTOM",
    )

    tipo: str = Field(
        default="PARCELA",
        description="ENTRADA | PARCELA | QUITACAO",
    )

    status: str = Field(
        default="PENDENTE",
        description="PENDENTE | PARCIAL | PAGO | ATRASADO | CANCELADO",
    )

    data_vencimento: datetime

    bloqueia_fluxo: bool = True


# =========================================================
# CREATE
# =========================================================
class PagamentoCreate(PagamentoBase):
    pass


# =========================================================
# UPDATE
# =========================================================
class PagamentoUpdate(BaseModel):
    status: Optional[str] = None
    data_pagamento: Optional[datetime] = None
    bloqueia_fluxo: Optional[bool] = None
    valor: Optional[float] = None
    modelo: Optional[str] = None


# =========================================================
# RESPONSE
# =========================================================
class PagamentoResponse(PagamentoBase):
    id: int
    project_id: int

    total: float
    data_pagamento: Optional[datetime]
    criado_automaticamente: bool

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
