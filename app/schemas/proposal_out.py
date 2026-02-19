from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class ProposalOut(BaseModel):
    id: int
    project_id: int
    area: float
    valor_base: float
    valor_art: float
    extras: float
    total: float

    # 🌐 URLs públicas (API)
    pdf_url: Optional[str] = None
    contract_url: Optional[str] = None

    created_at: datetime

    class Config:
        from_attributes = True
