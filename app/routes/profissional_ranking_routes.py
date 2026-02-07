from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.profissional_ranking import ProfissionalRankingResponse
from app.crud.profissional_ranking_crud import (
    recalcular_ranking_profissional,
    recalcular_todos,
    listar_ranking,
)

router = APIRouter()


# =========================================================
# RECALCULAR UM PROFISSIONAL
# =========================================================
@router.post("/ranking/profissionais/{profissional_id}")
def recalcular_profissional(
    profissional_id: int,
    db: Session = Depends(get_db),
):
    ranking = recalcular_ranking_profissional(db, profissional_id)
    return {
        "profissional_id": profissional_id,
        "score": ranking.score,
    }


# =========================================================
# RECALCULAR TODOS
# =========================================================
@router.post("/ranking/profissionais/recalcular-todos")
def recalcular_todos_route(
    db: Session = Depends(get_db),
):
    recalcular_todos(db)
    return {"status": "ranking recalculado"}


# =========================================================
# LISTAR RANKING
# =========================================================
@router.get(
    "/ranking/profissionais",
    response_model=list[ProfissionalRankingResponse],
)
def listar_ranking_route(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return listar_ranking(db, limit)
