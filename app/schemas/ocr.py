from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class OcrRequest(BaseModel):
    document_id: int
    provider: str = "NONE"


class OcrResponse(BaseModel):
    id: int
    document_id: int
    status: str
    provider: str

    texto_extraido: Optional[str]
    dados_extraidos_json: Optional[str]
    erro: Optional[str]

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
