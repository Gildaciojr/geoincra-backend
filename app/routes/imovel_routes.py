from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user_required
from app.models.user import User
from app.models.project import Project
from app.schemas.imovel import ImovelCreate, ImovelUpdate, ImovelResponse
from app.crud.imovel_crud import (
    create_imovel,
    list_imoveis_by_project,
    get_imovel,
    update_imovel,
    delete_imovel,
)

router = APIRouter(
    prefix="/projects/{project_id}/imoveis",
    tags=["Projetos - Imóveis"],
)


def _check_project_owner(db: Session, project_id: int, user_id: int) -> Project:
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.owner_id == user_id)
        .first()
    )
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projeto não encontrado ou acesso negado",
        )
    return project


# =====================================================
# CREATE
# =====================================================
@router.post("/", response_model=ImovelResponse)
def create_imovel_route(
    project_id: int,
    payload: ImovelCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    _check_project_owner(db, project_id, current_user.id)

    if payload.project_id != project_id:
        raise HTTPException(
            status_code=400,
            detail="project_id do payload não corresponde à rota",
        )

    return create_imovel(db, payload)


# =====================================================
# LIST
# =====================================================
@router.get("/", response_model=list[ImovelResponse])
def list_imoveis_route(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    _check_project_owner(db, project_id, current_user.id)
    return list_imoveis_by_project(db, project_id)


# =====================================================
# GET
# =====================================================
@router.get("/{imovel_id}", response_model=ImovelResponse)
def get_imovel_route(
    project_id: int,
    imovel_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    _check_project_owner(db, project_id, current_user.id)

    imovel = get_imovel(db, imovel_id)
    if not imovel or imovel.project_id != project_id:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")

    return imovel


# =====================================================
# UPDATE
# =====================================================
@router.put("/{imovel_id}", response_model=ImovelResponse)
def update_imovel_route(
    project_id: int,
    imovel_id: int,
    payload: ImovelUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    _check_project_owner(db, project_id, current_user.id)

    imovel = get_imovel(db, imovel_id)
    if not imovel or imovel.project_id != project_id:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")

    updated = update_imovel(db, imovel_id, payload)
    return updated


# =====================================================
# DELETE
# =====================================================
@router.delete("/{imovel_id}")
def delete_imovel_route(
    project_id: int,
    imovel_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    _check_project_owner(db, project_id, current_user.id)

    imovel = get_imovel(db, imovel_id)
    if not imovel or imovel.project_id != project_id:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")

    delete_imovel(db, imovel_id)
    return {"deleted": True}
