from datetime import datetime
from pydantic import BaseModel


class CartorioBase(BaseModel):
    nome: str
    tipo: str | None = None

    cns: str | None = None
    endereco: str | None = None
    telefone: str | None = None
    email: str | None = None

    municipio: str | None = None
    estado: str | None = None
    comarca: str | None = None


class CartorioCreate(CartorioBase):
    pass


class CartorioUpdate(BaseModel):
    nome: str | None = None
    tipo: str | None = None

    cns: str | None = None
    endereco: str | None = None
    telefone: str | None = None
    email: str | None = None

    municipio: str | None = None
    estado: str | None = None
    comarca: str | None = None


class CartorioRead(CartorioBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CartorioResponse(CartorioRead):
    pass
