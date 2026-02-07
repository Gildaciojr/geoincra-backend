# app/schemas/imovel.py

from datetime import datetime
from pydantic import BaseModel
from typing import Optional


# ============================================
# BASE
# ============================================
class ImovelBase(BaseModel):
    project_id: int
    municipio_id: int

    nome: Optional[str] = None
    descricao: Optional[str] = None

    area_hectares: float

    ccir: Optional[str] = None
    matricula_principal: Optional[str] = None


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

    class Config:
        from_attributes = True
