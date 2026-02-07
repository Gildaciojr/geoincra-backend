from datetime import datetime
from pydantic import BaseModel


class ProfissionalAvaliacaoCreate(BaseModel):
    project_id: int
    nota: float
    comentario: str | None = None
    origem: str = "INTERNA"


class ProfissionalAvaliacaoResponse(BaseModel):
    id: int
    profissional_id: int
    project_id: int
    nota: float
    comentario: str | None
    origem: str
    created_at: datetime

    class Config:
        from_attributes = True
