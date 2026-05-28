# app/schemas/imovel.py

from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


# ============================================
# BASE
# ============================================
class ImovelBase(BaseModel):
    project_id: int = Field(..., gt=0)
    municipio_id: int = Field(..., gt=0)

    nome: Optional[str] = Field(
    default=None,
    max_length=255,
    )
    descricao: Optional[str] = None

    area_hectares: float = Field(
    ...,
    gt=0,
    )

    ccir: Optional[str] = Field(
    default=None,
    max_length=50,
    )
    matricula_principal: Optional[str] = Field(
    default=None,
    max_length=100,
    )


# ============================================
# CREATE
# ============================================
class ImovelCreate(ImovelBase):
    pass


# ============================================
# UPDATE
# ============================================
class ImovelUpdate(BaseModel):
    municipio_id: Optional[int] = None
    nome: Optional[str] = None
    descricao: Optional[str] = None
    area_hectares: Optional[float] = None
    ccir: Optional[str] = None
    matricula_principal: Optional[str] = None


# ============================================
# RESPONSE
# ============================================
class ImovelResponse(ImovelBase):
    id: int
    created_at: datetime
    updated_at: datetime
    status_tecnico: str | None = None
    documento_origem_id: int | None = None

    class Config:
        from_attributes = True
