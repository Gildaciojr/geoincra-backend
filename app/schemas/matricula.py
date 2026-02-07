from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field


# =========================================================
# BASE
# =========================================================
class MatriculaBase(BaseModel):
    numero_matricula: str = Field(..., min_length=1, max_length=100)
    livro: Optional[str] = Field(default=None, max_length=50)
    folha: Optional[str] = Field(default=None, max_length=50)

    comarca: Optional[str] = Field(default=None, max_length=150)
    codigo_cartorio: Optional[str] = Field(default=None, max_length=50)

    data_abertura: Optional[date] = None
    data_ultima_atualizacao: Optional[date] = None

    inteiro_teor: Optional[str] = None
    arquivo_path: Optional[str] = Field(default=None, max_length=512)

    status: str = Field(
        default="ATIVA",
        description="ATIVA | CANCELADA | DESMEMBRADA | UNIFICADA",
        min_length=2,
        max_length=50,
    )

    observacoes: Optional[str] = None
    cartorio_id: Optional[int] = None


# =========================================================
# CREATE
# =========================================================
class MatriculaCreate(MatriculaBase):
    pass


# =========================================================
# UPDATE
# =========================================================
class MatriculaUpdate(BaseModel):
    numero_matricula: Optional[str] = Field(default=None, min_length=1, max_length=100)
    livro: Optional[str] = Field(default=None, max_length=50)
    folha: Optional[str] = Field(default=None, max_length=50)

    comarca: Optional[str] = Field(default=None, max_length=150)
    codigo_cartorio: Optional[str] = Field(default=None, max_length=50)

    data_abertura: Optional[date] = None
    data_ultima_atualizacao: Optional[date] = None

    inteiro_teor: Optional[str] = None
    arquivo_path: Optional[str] = Field(default=None, max_length=512)

    status: Optional[str] = Field(default=None, min_length=2, max_length=50)
    observacoes: Optional[str] = None
    cartorio_id: Optional[int] = None


# =========================================================
# RESPONSE
# =========================================================
class MatriculaResponse(MatriculaBase):
    id: int
    imovel_id: int

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
