from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.profissional_avaliacao import (
    ProfissionalAvaliacaoCreate,
    ProfissionalAvaliacaoResponse,
)
from app.crud.profissional_avaliacao_crud import (
    criar_avaliacao_profissional,
    listar_avaliacoes_por_profissional,
    get_avaliacao,
)

router = APIRouter()


# =========================================================
# CREATE
# =========================================================
@router.post(
    "/profissionais/{profissional_id}/avaliacoes",
    response_model=ProfissionalAvaliacaoResponse,
)
def criar_avaliacao_route(
    profissional_id: int,
    payload: ProfissionalAvaliacaoCreate,
    db: Session = Depends(get_db),
):
    try:
        return criar_avaliacao_profissional(db, profissional_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# =========================================================
# LIST
# =========================================================
@router.get(
    "/profissionais/{profissional_id}/avaliacoes",
    response_model=list[ProfissionalAvaliacaoResponse],
)
def listar_avaliacoes_route(
    profissional_id: int,
    db: Session = Depends(get_db),
):
    return listar_avaliacoes_por_profissional(db, profissional_id)


# =========================================================
# GET
# =========================================================
@router.get(
    "/avaliacoes/{avaliacao_id}",
    response_model=ProfissionalAvaliacaoResponse,
)
def get_avaliacao_route(
    avaliacao_id: int,
    db: Session = Depends(get_db),
):
    avaliacao = get_avaliacao(db, avaliacao_id)
    if not avaliacao:
        raise HTTPException(status_code=404, detail="Avaliação não encontrada.")
    return avaliacao
