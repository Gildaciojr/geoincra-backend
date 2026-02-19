from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ProposalCreate(BaseModel):
    project_id: int
    area: float
    valor_base: float
    valor_art: float
    extras: float
    total: float

    html_proposta: str
    html_contrato: str

    # 🔒 paths internos (storage)
    pdf_path: Optional[str] = None
    contract_pdf_path: Optional[str] = None

    created_at: Optional[datetime] = None
