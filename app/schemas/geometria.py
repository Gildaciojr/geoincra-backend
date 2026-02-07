from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional


class GeometriaBase(BaseModel):
    nome: Optional[str] = None
    observacoes: Optional[str] = None
    geojson: str = Field(..., min_length=10)
    epsg_origem: int = 4326


class GeometriaCreate(GeometriaBase):
    pass


class GeometriaUpdate(BaseModel):
    nome: Optional[str] = None
    observacoes: Optional[str] = None
    geojson: Optional[str] = None
    epsg_origem: Optional[int] = None


class GeometriaResponse(GeometriaBase):
    id: int
    imovel_id: int

    epsg_utm: Optional[int] = None
    area_hectares: Optional[float] = None
    perimetro_m: Optional[float] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
