# app/routes/proprietario_routes.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.proprietario import (
    ProprietarioCreate,
    ProprietarioUpdate,
    ProprietarioResponse,
)
from app.crud.proprietario_crud import (
    create_proprietario,
    list_proprietarios_by_imovel,
    get_proprietario,
    update_proprietario,
    delete_proprietario,
)

router = APIRouter()


# =========================================================
# CREATE
# =========================================================
@router.post(
    "/imoveis/{imovel_id}/proprietarios/",
    response_model=ProprietarioResponse,
)
def create_proprietario_route(
    imovel_id: int,
    payload: ProprietarioCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_proprietario(db, imovel_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# =========================================================
# LIST
# =========================================================
@router.get(
    "/imoveis/{imovel_id}/proprietarios/",
    response_model=list[ProprietarioResponse],
)
def list_proprietarios_route(
    imovel_id: int,
    db: Session = Depends(get_db),
):
    return list_proprietarios_by_imovel(db, imovel_id)


# =========================================================
# GET
# =========================================================
@router.get(
    "/proprietarios/{proprietario_id}",
    response_model=ProprietarioResponse,
)
def get_proprietario_route(
    proprietario_id: int,
    db: Session = Depends(get_db),
):
    proprietario = get_proprietario(db, proprietario_id)
    if not proprietario:
        raise HTTPException(
            status_code=404,
            detail="Proprietário não encontrado.",
        )
    return proprietario


# =========================================================
# UPDATE
# =========================================================
@router.put(
    "/proprietarios/{proprietario_id}",
    response_model=ProprietarioResponse,
)
def update_proprietario_route(
    proprietario_id: int,
    payload: ProprietarioUpdate,
    db: Session = Depends(get_db),
):
    proprietario = update_proprietario(db, proprietario_id, payload)
    if not proprietario:
        raise HTTPException(
            status_code=404,
            detail="Proprietário não encontrado.",
        )
    return proprietario


# =========================================================
# DELETE
# =========================================================
@router.delete("/proprietarios/{proprietario_id}")
def delete_proprietario_route(
    proprietario_id: int,
    db: Session = Depends(get_db),
):
    success = delete_proprietario(db, proprietario_id)
    if not success:
        raise HTTPException(
            status_code=404,
            detail="Proprietário não encontrado.",
        )
    return {"deleted": True}
