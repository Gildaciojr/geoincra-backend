from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class PagamentoEventoResponse(BaseModel):
    id: int
    pagamento_id: int
    tipo: str = Field(..., min_length=1, max_length=40)
    descricao: Optional[str] = None
    metadata_json: Optional[Dict[str, Any]] = None
    criado_por_usuario_id: Optional[int] = None
    criado_em: datetime

    class Config:
        from_attributes = True
