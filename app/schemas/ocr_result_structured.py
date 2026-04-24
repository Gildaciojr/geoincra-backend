from __future__ import annotations

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


# =========================================================
# SEGMENTO
# =========================================================
class SegmentoOCR(BaseModel):
    azimute_raw: Optional[str] = None
    distancia: float = Field(..., gt=0)

    @field_validator("azimute_raw", mode="before")
    @classmethod
    def resolver_azimute(cls, v, info):
        if v and str(v).strip():
            return str(v).strip()

        data = info.data if hasattr(info, "data") else {}

        return (
            data.get("azimute")
            or data.get("rumo")
            or data.get("bearing")
            or data.get("valor")
            or data.get("azimute_decimal")
        )

    @field_validator("azimute_raw")
    @classmethod
    def validar_azimute(cls, v: Optional[str]) -> str:
        if not v or not str(v).strip():
            raise ValueError("Azimute vazio ou não identificado")
        return str(v).strip()


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
# 🔥 NOVO — ATO REGISTRAL (CRÍTICO)
# =========================================================
class AtoRegistralOCR(BaseModel):
    tipo: Optional[str]  # R, AV, etc
    numero: Optional[str]  # ex: 4 (R-4)
    codigo: Optional[str]  # ex: R-4, AV-3

    descricao: Optional[str]

    data: Optional[str]
    protocolo: Optional[str]

    valor: Optional[float]

    envolvidos: List[Dict[str, Optional[str]]] = []

    texto_original: Optional[str]


# =========================================================
# 🔥 NOVO — HISTÓRICO COMPLETO
# =========================================================
class HistoricoMatriculaOCR(BaseModel):
    atos: List[AtoRegistralOCR] = []


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

    # 🔥 NOVO (NÃO OBRIGATÓRIO → NÃO QUEBRA PIPELINE)
    historico: Optional[HistoricoMatriculaOCR] = None

    qualidade: QualidadeOCR

    @field_validator("proprietarios")
    @classmethod
    def validar_proprietarios(cls, v):
        if not v:
            raise ValueError("OCR sem proprietários válidos")
        return v