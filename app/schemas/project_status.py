from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


# =========================================================
# BASE
# =========================================================
class ProjectStatusBase(BaseModel):
    status: str = Field(..., min_length=3, max_length=60)
    descricao: Optional[str] = None

    definido_automaticamente: bool = False
    definido_por_usuario_id: Optional[int] = None


# =========================================================
# CREATE
# =========================================================
class ProjectStatusCreate(ProjectStatusBase):
    pass


# =========================================================
# RESPONSE
# =========================================================
class ProjectStatusResponse(ProjectStatusBase):
    id: int
    project_id: int
    ativo: bool
    definido_em: datetime
    created_at: datetime

    class Config:
        from_attributes = True
