from pydantic import BaseModel, Field
from typing import Optional


class ConfrontanteBase(BaseModel):
    direcao: str
    nome_confrontante: Optional[str] = None
    matricula_confrontante: Optional[str] = None
    identificacao_imovel_confrontante: Optional[str] = None
    descricao: Optional[str] = None
    geometria_id: Optional[int] = None
    matricula_id: Optional[int] = None
    direcao_normalizada: Optional[str] = None
    ordem_segmento: Optional[int] = None
    lado_label: Optional[str] = None
    observacoes: Optional[str] = None
    tipo: Optional[str] = Field(default=None, max_length=50)
    lote: Optional[str] = Field(default=None, max_length=50)
    gleba: Optional[str] = Field(default=None, max_length=50)


class ConfrontanteCreate(ConfrontanteBase):
    pass


class ConfrontanteUpdate(BaseModel):
    direcao: Optional[str] = None
    nome_confrontante: Optional[str] = None
    matricula_confrontante: Optional[str] = None
    identificacao_imovel_confrontante: Optional[str] = None
    descricao: Optional[str] = None
    geometria_id: Optional[int] = None
    matricula_id: Optional[int] = None
    direcao_normalizada: Optional[str] = None
    ordem_segmento: Optional[int] = None
    lado_label: Optional[str] = None
    observacoes: Optional[str] = None
    tipo: Optional[str] = Field(default=None, max_length=50)
    lote: Optional[str] = Field(default=None, max_length=50)
    gleba: Optional[str] = Field(default=None, max_length=50)


class ConfrontanteResponse(ConfrontanteBase):
    id: int
    imovel_id: int

    class Config:
        from_attributes = True
