from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, model_validator


# =========================================================
# BASE COMUM
# =========================================================
class ProfissionalBase(BaseModel):
    nome_completo: str = Field(..., min_length=3, max_length=255)
    tipo_pessoa: str = Field(..., description="FISICA | JURIDICA")

    cpf: Optional[str] = Field(default=None, min_length=11, max_length=14)
    cnpj: Optional[str] = Field(default=None, min_length=14, max_length=18)

    email: Optional[str] = Field(default=None, max_length=255)
    telefone: Optional[str] = Field(default=None, max_length=50)

    numero_registro: Optional[str] = Field(default=None, min_length=2, max_length=50)
    uf_registro: Optional[str] = Field(default=None, min_length=2, max_length=2)

    especialidades: Optional[str] = Field(
        default=None,
        description="Lista livre de especialidades técnicas",
    )

    ativo: bool = True

    avaliacao_media: Optional[float] = Field(
        default=None,
        ge=0,
        le=5,
        description="Avaliação média (0 a 5)",
    )

    total_projetos: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_documentos(self):
        tipo = (self.tipo_pessoa or "").upper()

        if tipo not in {"FISICA", "JURIDICA"}:
            raise ValueError("tipo_pessoa deve ser FISICA ou JURIDICA")

        if tipo == "FISICA" and not self.cpf:
            raise ValueError("CPF é obrigatório para profissional do tipo FISICA")

        if tipo == "JURIDICA" and not self.cnpj:
            raise ValueError("CNPJ é obrigatório para profissional do tipo JURIDICA")

        if not self.numero_registro:
            raise ValueError("numero_registro é obrigatório")

        if not self.uf_registro:
            raise ValueError("uf_registro é obrigatório")

        return self


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
    tipo_pessoa: Optional[str] = Field(default=None, description="FISICA | JURIDICA")

    cpf: Optional[str] = Field(default=None, min_length=11, max_length=14)
    cnpj: Optional[str] = Field(default=None, min_length=14, max_length=18)

    email: Optional[str] = Field(default=None, max_length=255)
    telefone: Optional[str] = Field(default=None, max_length=50)

    numero_registro: Optional[str] = Field(default=None, min_length=2, max_length=50)
    uf_registro: Optional[str] = Field(default=None, min_length=2, max_length=2)

    especialidades: Optional[str] = None
    ativo: Optional[bool] = None

    avaliacao_media: Optional[float] = Field(default=None, ge=0, le=5)
    total_projetos: Optional[int] = Field(default=None, ge=0)


# =========================================================
# RESPONSE
# =========================================================
class ProfissionalResponse(BaseModel):
    id: int
    nome_completo: str
    tipo_pessoa: str

    cpf: Optional[str] = None
    cnpj: Optional[str] = None

    email: Optional[str] = None
    telefone: Optional[str] = None

    crea: Optional[str] = None
    uf_crea: Optional[str] = None

    especialidades: Optional[str] = None
    ativo: bool

    rating_medio: float
    total_servicos: int

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True