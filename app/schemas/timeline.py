from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class TimelineBase(BaseModel):
    titulo: str
    descricao: Optional[str] = None
    status: Optional[str] = None
    etapa: Optional[str] = None
    created_by_user_id: Optional[int] = None


class TimelineCreate(TimelineBase):
    """
    ⚠️ IMPORTANTE:
    NÃO contém project_id.

    O project_id vem exclusivamente pela rota:
    /projects/{project_id}/timeline

    Isso evita inconsistência e conflitos de dados.
    """
    pass


class TimelineResponse(TimelineBase):
    id: int
    project_id: int
    created_at: datetime

    class Config:
        from_attributes = True