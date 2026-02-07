from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user_required
from app.schemas.matricula import MatriculaCreate, MatriculaUpdate, MatriculaResponse
from app.crud.matricula_crud import (
    create_matricula,
    list_matriculas_by_imovel,
    get_matricula,
    update_matricula,
    delete_matricula,
)

router = APIRouter(tags=["Matrículas"])


# =========================================================
# 🔒 CREATE
# =========================================================
@router.post("/imoveis/{imovel_id}/matriculas", response_model=MatriculaResponse)
def criar_matricula(
    imovel_id: int,
    payload: MatriculaCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_required),
):
    try:
        return create_matricula(db, imovel_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# =========================================================
# 🔓 LIST
# =========================================================
@router.get("/imoveis/{imovel_id}/matriculas", response_model=list[MatriculaResponse])
def listar_matriculas(imovel_id: int, db: Session = Depends(get_db)):
    return list_matriculas_by_imovel(db, imovel_id)


# =========================================================
# 🔓 GET
# =========================================================
@router.get("/matriculas/{matricula_id}", response_model=MatriculaResponse)
def obter_matricula(matricula_id: int, db: Session = Depends(get_db)):
    obj = get_matricula(db, matricula_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Matrícula não encontrada.")
    return obj


# =========================================================
# 🔒 UPDATE
# =========================================================
@router.put("/matriculas/{matricula_id}", response_model=MatriculaResponse)
def atualizar_matricula(
    matricula_id: int,
    payload: MatriculaUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_required),
):
    obj = update_matricula(db, matricula_id, payload)
    if not obj:
        raise HTTPException(status_code=404, detail="Matrícula não encontrada.")
    return obj


# =========================================================
# 🔒 DELETE
# =========================================================
@router.delete("/matriculas/{matricula_id}")
def deletar_matricula(
    matricula_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_required),
):
    ok = delete_matricula(db, matricula_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Matrícula não encontrada.")
    return {"deleted": True, "id": matricula_id}
