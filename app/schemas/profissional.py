from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# =========================================================
# BASE
# =========================================================
class ProfissionalBase(BaseModel):
    nome_completo: str = Field(..., min_length=3, max_length=255)

    cpf: str = Field(..., min_length=11, max_length=14)

    email: Optional[str] = Field(default=None, max_length=255)
    telefone: Optional[str] = Field(default=None, max_length=50)

    conselho: str = Field(
        default="CREA",
        min_length=2,
        max_length=30,
        description="CREA | CFT | CAU (expansível)",
    )

    numero_registro: str = Field(..., min_length=2, max_length=50)
    uf_registro: str = Field(..., min_length=2, max_length=2)

    especialidades: Optional[str] = Field(
        default=None,
        description="Lista livre de especialidades técnicas",
    )

    ativo: bool = True

    avaliacao_media: Optional[int] = Field(
        default=None,
        ge=1,
        le=5,
        description="Avaliação média (1 a 5)",
    )

    total_projetos: int = Field(default=0, ge=0)

    observacoes: Optional[str] = None


# =========================================================
# CREATE
# =========================================================
class ProfissionalCreate(ProfissionalBase):
    pass


# =========================================================
# UPDATE
# =========================================================
class ProfissionalUpdate(BaseModel):
    nome_completo: Optional[str] = Field(default=None, min_length=3, max_length=255)

    email: Optional[str] = Field(default=None, max_length=255)
    telefone: Optional[str] = Field(default=None, max_length=50)

    especialidades: Optional[str] = None
    ativo: Optional[bool] = None

    avaliacao_media: Optional[int] = Field(default=None, ge=1, le=5)

    observacoes: Optional[str] = None


# =========================================================
# RESPONSE
# =========================================================
class ProfissionalResponse(ProfissionalBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
