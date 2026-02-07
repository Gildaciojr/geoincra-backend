# app/schemas/memorial.py

from pydantic import BaseModel, Field
from typing import List
from datetime import datetime


class MemorialLinha(BaseModel):
    ordem: int
    de_vertice: str
    ate_vertice: str
    azimute_graus: float = Field(..., ge=0.0, lt=360.0)
    rumo: str
    distancia_m: float = Field(..., ge=0.0)


class MemorialResponse(BaseModel):
    geometria_id: int
    epsg_utm: int
    area_hectares: float
    perimetro_m: float
    linhas: List[MemorialLinha]
    texto: str
    gerado_em: datetime
