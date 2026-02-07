from sqlalchemy.orm import Session

from app.models.profissional_ranking import ProfissionalRanking
from app.services.profissional_ranking_service import ProfissionalRankingService


def recalcular_ranking_profissional(
    db: Session,
    profissional_id: int,
) -> ProfissionalRanking:
    return ProfissionalRankingService.recalcular_ranking_profissional(
        db,
        profissional_id,
    )


def recalcular_todos(db: Session) -> None:
    ProfissionalRankingService.recalcular_todos(db)


def listar_ranking(
    db: Session,
    limit: int = 10,
) -> list[ProfissionalRanking]:
    return ProfissionalRankingService.melhores_profissionais(db, limit)
