from pydantic import BaseModel
from typing import Optional


class ConfrontanteBase(BaseModel):
    direcao: str
    nome_confrontante: Optional[str] = None
    matricula_confrontante: Optional[str] = None
    identificacao_imovel_confrontante: Optional[str] = None
    descricao: Optional[str] = None


class ConfrontanteCreate(ConfrontanteBase):
    pass


class ConfrontanteUpdate(BaseModel):
    direcao: Optional[str] = None
    nome_confrontante: Optional[str] = None
    matricula_confrontante: Optional[str] = None
    identificacao_imovel_confrontante: Optional[str] = None
    descricao: Optional[str] = None


class ConfrontanteResponse(ConfrontanteBase):
    id: int
    imovel_id: int

    class Config:
        from_attributes = True
