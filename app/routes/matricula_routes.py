from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user_required
from app.models.user import User
from app.models.project import Project
from app.models.imovel import Imovel
from app.schemas.matricula import (
    MatriculaCreate,
    MatriculaUpdate,
    MatriculaResponse,
)
from app.crud.matricula_crud import (
    create_matricula,
    list_matriculas_by_imovel,
    get_matricula,
    update_matricula,
    delete_matricula,
)

router = APIRouter(
    prefix="/projects/{project_id}/imoveis/{imovel_id}/matriculas",
    tags=["Projetos - Matrículas"],
)


def _check_access(
    db: Session,
    project_id: int,
    imovel_id: int,
    user_id: int,
) -> Imovel:
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.owner_id == user_id)
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    imovel = (
        db.query(Imovel)
        .filter(Imovel.id == imovel_id, Imovel.project_id == project_id)
        .first()
    )
    if not imovel:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")

    return imovel


# =========================================================
# CREATE
# =========================================================
@router.post("/", response_model=MatriculaResponse)
def create_matricula_route(
    project_id: int,
    imovel_id: int,
    payload: MatriculaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    _check_access(db, project_id, imovel_id, current_user.id)
    return create_matricula(db, imovel_id, payload)


# =========================================================
# LIST
# =========================================================
@router.get("/", response_model=list[MatriculaResponse])
def list_matriculas_route(
    project_id: int,
    imovel_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    _check_access(db, project_id, imovel_id, current_user.id)
    return list_matriculas_by_imovel(db, imovel_id)


# =========================================================
# GET
# =========================================================
@router.get("/{matricula_id}", response_model=MatriculaResponse)
def get_matricula_route(
    project_id: int,
    imovel_id: int,
    matricula_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    _check_access(db, project_id, imovel_id, current_user.id)

    obj = get_matricula(db, matricula_id)
    if not obj or obj.imovel_id != imovel_id:
        raise HTTPException(status_code=404, detail="Matrícula não encontrada")

    return obj


# =========================================================
# UPDATE
# =========================================================
@router.put("/{matricula_id}", response_model=MatriculaResponse)
def update_matricula_route(
    project_id: int,
    imovel_id: int,
    matricula_id: int,
    payload: MatriculaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    _check_access(db, project_id, imovel_id, current_user.id)

    obj = get_matricula(db, matricula_id)
    if not obj or obj.imovel_id != imovel_id:
        raise HTTPException(status_code=404, detail="Matrícula não encontrada")

    updated = update_matricula(db, matricula_id, payload)
    return updated


# =========================================================
# DELETE
# =========================================================
@router.delete("/{matricula_id}")
def delete_matricula_route(
    project_id: int,
    imovel_id: int,
    matricula_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    _check_access(db, project_id, imovel_id, current_user.id)

    obj = get_matricula(db, matricula_id)
    if not obj or obj.imovel_id != imovel_id:
        raise HTTPException(status_code=404, detail="Matrícula não encontrada")

    delete_matricula(db, matricula_id)
    return {"deleted": True}
