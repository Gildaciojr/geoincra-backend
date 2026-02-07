# app/schemas/sobreposicao.py

from datetime import datetime
from pydantic import BaseModel


class SobreposicaoBase(BaseModel):
    geometria_base_id: int
    geometria_afetada_id: int
    tipo: str


class SobreposicaoResponse(SobreposicaoBase):
    id: int
    area_sobreposta_ha: float
    percentual_sobreposicao: float
    created_at: datetime

    class Config:
        from_attributes = True
