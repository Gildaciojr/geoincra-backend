from datetime import datetime
from pydantic import BaseModel
from typing import Optional, Dict, Any


class OcrRequest(BaseModel):

    document_id: int
    provider: str = "GOOGLE"
    prompt_id: Optional[int] = None


class OcrResponse(BaseModel):

    id: int
    document_id: int
    status: str
    provider: str

    texto_extraido: Optional[str]

    # 🔥 agora JSON real
    dados_extraidos_json: Optional[Dict[str, Any]]

    erro: Optional[str]

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True