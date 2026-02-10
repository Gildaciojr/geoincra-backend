from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# ============================================
# BASE
# ============================================
class ProjectBase(BaseModel):
    name: str
    descricao_simplificada: Optional[str] = None
    tipo_processo: Optional[str] = None

    municipio: Optional[str] = None
    uf: Optional[str] = None

    codigo_imovel_rural: Optional[str] = None
    codigo_sncr: Optional[str] = None
    codigo_car: Optional[str] = None
    codigo_sigef: Optional[str] = None

    observacoes: Optional[str] = None
    status: Optional[str] = None


# ============================================
# CREATE
# ============================================
class ProjectCreate(ProjectBase):
    name: str


# ============================================
# UPDATE
# ============================================
class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    descricao_simplificada: Optional[str] = None
    tipo_processo: Optional[str] = None

    municipio: Optional[str] = None
    uf: Optional[str] = None

    codigo_imovel_rural: Optional[str] = None
    codigo_sncr: Optional[str] = None
    codigo_car: Optional[str] = None
    codigo_sigef: Optional[str] = None

    observacoes: Optional[str] = None
    status: Optional[str] = None


# ============================================
# RESPONSE
# ============================================
class ProjectResponse(ProjectBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ProjectCardResponse(BaseModel):
    id: int
    name: str
    municipio: str | None
    uf: str | None
    status: str
    created_at: datetime

    total_documents: int = 0
    total_proposals: int = 0

    class Config:
        from_attributes = True

