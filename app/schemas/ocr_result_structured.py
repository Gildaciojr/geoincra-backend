from __future__ import annotations

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


# =========================================================
# SEGMENTO
# =========================================================
class SegmentoOCR(BaseModel):
    azimute_raw: str = Field(..., min_length=2)
    distancia: float = Field(..., gt=0)

    @field_validator("azimute_raw")
    @classmethod
    def validar_azimute(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Azimute vazio")
        return v


# =========================================================
# ÁREA
# =========================================================
class AreaOCR(BaseModel):
    valor: Optional[float]
    unidade_original: Optional[str]
    hectares: Optional[float]


# =========================================================
# IMÓVEL
# =========================================================
class ImovelOCR(BaseModel):
    descricao: Optional[str]
    area: AreaOCR


# =========================================================
# MATRÍCULA
# =========================================================
class MatriculaOCR(BaseModel):
    numero: Optional[str]
    comarca: Optional[str]
    cartorio: Optional[str]


# =========================================================
# PROPRIETÁRIO
# =========================================================
class ProprietarioOCR(BaseModel):
    nome: str = Field(..., min_length=3)
    cpf_cnpj: Optional[str]


# =========================================================
# GEOMETRIA
# =========================================================
class GeometriaOCR(BaseModel):
    fonte: Optional[str]
    geojson: Optional[Dict[str, Any]]
    segmentos: List[SegmentoOCR] = []
    memorial_texto: Optional[str]


# =========================================================
# QUALIDADE
# =========================================================
class QualidadeOCR(BaseModel):
    score: int = Field(..., ge=0, le=100)
    erros: List[str] = []
    warnings: List[str] = []


# =========================================================
# ROOT
# =========================================================
class OCRStructured(BaseModel):
    matricula: MatriculaOCR
    imovel: ImovelOCR
    proprietarios: List[ProprietarioOCR]
    geometria: GeometriaOCR
    confrontantes: List[Dict[str, Optional[str]]] = []
    qualidade: QualidadeOCR

    @field_validator("proprietarios")
    @classmethod
    def validar_proprietarios(cls, v):
        if not v:
            raise ValueError("OCR sem proprietários válidos")
        return v