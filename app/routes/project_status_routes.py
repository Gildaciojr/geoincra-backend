from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.project_status import (
    ProjectStatusCreate,
    ProjectStatusResponse,
)
from app.crud.project_status_crud import (
    definir_status_projeto,
    obter_status_atual,
    listar_historico_status,
)
from app.crud.project_crud import get_project

router = APIRouter()


@router.post("/projects/{project_id}/status", response_model=ProjectStatusResponse)
def definir_status(
    project_id: int,
    payload: ProjectStatusCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project(db, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    return definir_status_projeto(db, project_id, payload)


@router.get(
    "/projects/{project_id}/status/atual",
    response_model=ProjectStatusResponse,
)
def status_atual(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project(db, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    status = obter_status_atual(db, project_id)
    if not status:
        raise HTTPException(status_code=404, detail="Status não definido.")

    return status


@router.get(
    "/projects/{project_id}/status/historico",
    response_model=list[ProjectStatusResponse],
)
def historico_status(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project(db, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    return listar_historico_status(db, project_id)
