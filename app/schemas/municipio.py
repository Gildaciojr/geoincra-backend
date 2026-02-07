from pydantic import BaseModel
from typing import Optional


class MunicipioBase(BaseModel):
    nome: str
    estado: str
    vti_min: float
    vtn_min: float


class MunicipioCreate(MunicipioBase):
    pass


class MunicipioUpdate(BaseModel):
    nome: Optional[str] = None
    estado: Optional[str] = None
    vti_min: Optional[float] = None
    vtn_min: Optional[float] = None


class MunicipioResponse(MunicipioBase):
    id: int

    class Config:
        from_attributes = True
