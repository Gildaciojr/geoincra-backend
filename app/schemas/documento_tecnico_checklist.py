from datetime import datetime
from typing import Optional
from enum import Enum

from pydantic import BaseModel, Field


# =========================================================
# ENUM DE STATUS (CRÍTICO PARA CONSISTÊNCIA)
# =========================================================
class DocumentoChecklistStatus(str, Enum):
    NA = "NA"
    OK = "OK"
    ALERTA = "ALERTA"
    ERRO = "ERRO"


# =========================================================
# BASE
# =========================================================
class DocumentoTecnicoChecklistBase(BaseModel):
    chave: str = Field(..., min_length=2, max_length=80)
    descricao: str = Field(..., min_length=3, max_length=255)

    obrigatorio: bool = True

    status: DocumentoChecklistStatus = Field(
        default=DocumentoChecklistStatus.NA,
        description="NA | OK | ALERTA | ERRO",
    )

    mensagem: Optional[str] = None

    validado_automaticamente: bool = False


# =========================================================
# CREATE
# =========================================================
class DocumentoTecnicoChecklistCreate(DocumentoTecnicoChecklistBase):
    pass


# =========================================================
# UPDATE / VALIDAÇÃO
# =========================================================
class DocumentoTecnicoChecklistUpdate(BaseModel):
    status: Optional[DocumentoChecklistStatus] = None
    mensagem: Optional[str] = None
    validado_automaticamente: Optional[bool] = None
    validado_por_usuario_id: Optional[int] = None


# =========================================================
# RESPONSE
# =========================================================
class DocumentoTecnicoChecklistResponse(DocumentoTecnicoChecklistBase):
    id: int
    documento_tecnico_id: int

    validado_por_usuario_id: Optional[int]
    validado_em: Optional[datetime]

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True