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

    pdf_path: Optional[str]
    contract_pdf_path: Optional[str]

    created_at: datetime

    class Config:
        from_attributes = True
