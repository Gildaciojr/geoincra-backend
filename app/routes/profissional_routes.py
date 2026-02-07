from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.profissional import (
    ProfissionalCreate,
    ProfissionalUpdate,
    ProfissionalResponse,
)
from app.crud.profissional_crud import (
    create_profissional,
    list_profissionais,
    get_profissional,
    update_profissional,
    delete_profissional,
)

router = APIRouter()


# =========================================================
# CREATE
# =========================================================
@router.post(
    "/profissionais/",
    response_model=ProfissionalResponse,
)
def create_profissional_route(
    payload: ProfissionalCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_profissional(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =========================================================
# LIST
# =========================================================
@router.get(
    "/profissionais/",
    response_model=list[ProfissionalResponse],
)
def list_profissionais_route(
    db: Session = Depends(get_db),
):
    return list_profissionais(db)


# =========================================================
# GET
# =========================================================
@router.get(
    "/profissionais/{profissional_id}",
    response_model=ProfissionalResponse,
)
def get_profissional_route(
    profissional_id: int,
    db: Session = Depends(get_db),
):
    profissional = get_profissional(db, profissional_id)
    if not profissional:
        raise HTTPException(status_code=404, detail="Profissional não encontrado.")
    return profissional


# =========================================================
# UPDATE
# =========================================================
@router.put(
    "/profissionais/{profissional_id}",
    response_model=ProfissionalResponse,
)
def update_profissional_route(
    profissional_id: int,
    payload: ProfissionalUpdate,
    db: Session = Depends(get_db),
):
    profissional = update_profissional(db, profissional_id, payload)
    if not profissional:
        raise HTTPException(status_code=404, detail="Profissional não encontrado.")
    return profissional


# =========================================================
# DELETE (DESATIVAR)
# =========================================================
@router.delete("/profissionais/{profissional_id}")
def delete_profissional_route(
    profissional_id: int,
    db: Session = Depends(get_db),
):
    ok = delete_profissional(db, profissional_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Profissional não encontrado.")
    return {"desativado": True}
