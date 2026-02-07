from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# =========================================================
# BASE
# =========================================================
class PropostaProfissionalBase(BaseModel):
    valor_proposto: Optional[int] = Field(default=None, ge=0)
    prazo_dias: Optional[int] = Field(default=None, ge=1)

    observacoes: Optional[str] = None


# =========================================================
# CREATE (ENVIO)
# =========================================================
class PropostaProfissionalCreate(PropostaProfissionalBase):
    profissional_id: int = Field(..., ge=1)


# =========================================================
# RESPOSTA (ACEITAR / RECUSAR)
# =========================================================
class PropostaProfissionalResposta(BaseModel):
    aceitar: bool
    observacoes: Optional[str] = None


# =========================================================
# RESPONSE
# =========================================================
class PropostaProfissionalResponse(PropostaProfissionalBase):
    id: int
    project_id: int
    profissional_id: int

    status: str

    enviada_em: datetime
    respondida_em: Optional[datetime]

    class Config:
        from_attributes = True
