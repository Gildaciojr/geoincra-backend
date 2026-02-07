from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SigefCsvExportRequest(BaseModel):
    geometria_id: int = Field(..., ge=1)

    # Identificação opcional do produto/arquivo
    document_group_key: str = Field(default="PLANILHA_SIGEF_CSV", min_length=2, max_length=80)
    tipo: str = Field(default="Planilha SIGEF (CSV)", min_length=2, max_length=120)

    # Prefixo do vértice (V1, V2...)
    prefixo_vertice: str = Field(default="V", min_length=1, max_length=10)

    # Se True, retorna também o conteúdo do CSV na resposta
    incluir_conteudo: bool = False

    # Observação técnica opcional
    observacoes_tecnicas: Optional[str] = None


class SigefCsvExportResponse(BaseModel):
    sucesso: bool
    mensagem: str

    geometria_id: int
    imovel_id: int

    epsg_origem: int
    epsg_utm: int

    area_hectares: float
    perimetro_m: float

    documento_tecnico_id: int
    versao: int

    arquivo_path: str
    gerado_em: datetime

    conteudo_csv: Optional[str] = None
