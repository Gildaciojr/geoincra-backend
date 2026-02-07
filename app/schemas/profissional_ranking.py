from datetime import datetime
from pydantic import BaseModel


class ProfissionalRankingResponse(BaseModel):
    id: int
    profissional_id: int
    score: float
    avaliacao_media: float | None
    total_projetos: int
    ativo: bool
    calculado_em: datetime

    class Config:
        from_attributes = True
