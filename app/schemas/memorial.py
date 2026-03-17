from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class MemorialLinha(BaseModel):
    ordem: int
    de_vertice: str
    ate_vertice: str
    azimute_graus: float = Field(..., ge=0.0, lt=360.0)
    rumo: str
    distancia_m: float = Field(..., ge=0.0)


class MemorialResponse(BaseModel):
    geometria_id: int
    epsg_utm: Optional[int] = None
    tipo_referencial: str
    area_hectares: float
    perimetro_m: float
    linhas: List[MemorialLinha]
    texto: str
    gerado_em: datetime