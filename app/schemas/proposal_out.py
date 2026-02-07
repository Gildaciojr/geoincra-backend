from datetime import datetime
from pydantic import BaseModel


class ProposalOut(BaseModel):
    id: int
    project_id: int
    area: float
    total: float
    pdf_path: str | None
    contract_pdf_path: str | None
    created_at: datetime

    class Config:
        from_attributes = True
