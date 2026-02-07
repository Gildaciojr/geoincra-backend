from datetime import datetime
from typing import Optional
from pydantic import BaseModel


# =========================================================
# BASE
# =========================================================

class ProprietarioBase(BaseModel):
    nome_completo: str

    tipo_pessoa: str = "FISICA"  # FISICA | JURIDICA

    cpf: Optional[str] = None
    cnpj: Optional[str] = None

    rg: Optional[str] = None
    orgao_emissor: Optional[str] = None

    estado_civil: Optional[str] = None
    profissao: Optional[str] = None
    nacionalidade: Optional[str] = None

    endereco: Optional[str] = None
    municipio: Optional[str] = None
    estado: Optional[str] = None
    cep: Optional[str] = None

    telefone: Optional[str] = None
    email: Optional[str] = None

    observacoes: Optional[str] = None


# =========================================================
# CREATE
# =========================================================

class ProprietarioCreate(ProprietarioBase):
    pass


# =========================================================
# UPDATE
# =========================================================

class ProprietarioUpdate(BaseModel):
    nome_completo: Optional[str] = None
    tipo_pessoa: Optional[str] = None

    cpf: Optional[str] = None
    cnpj: Optional[str] = None

    rg: Optional[str] = None
    orgao_emissor: Optional[str] = None

    estado_civil: Optional[str] = None
    profissao: Optional[str] = None
    nacionalidade: Optional[str] = None

    endereco: Optional[str] = None
    municipio: Optional[str] = None
    estado: Optional[str] = None
    cep: Optional[str] = None

    telefone: Optional[str] = None
    email: Optional[str] = None

    observacoes: Optional[str] = None


# =========================================================
# RESPONSE
# =========================================================

class ProprietarioResponse(ProprietarioBase):
    id: int
    imovel_id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
