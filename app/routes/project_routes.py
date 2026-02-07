from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import (
    get_db,
    get_current_user_optional,
    get_current_user_required,
)
from app.models.user import User
from app.schemas.project import ProjectCreate, ProjectUpdate, ProjectResponse
from app.crud.project_crud import (
    create_project,
    list_projects,
    get_project,
    update_project,
    delete_project,
)

router = APIRouter(prefix="/projects", tags=["Projetos"])


# ============================================================
# 🔒 CRIAR PROJETO → exige login
# ============================================================
@router.post("/", response_model=ProjectResponse)
def create_project_route(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    return create_project(db, payload, owner_id=current_user.id)


# ============================================================
# 🔓 LISTAR PROJETOS → visitante ou usuário
# ============================================================
@router.get("/", response_model=list[ProjectResponse])
def list_projects_route(
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    # Visitante → lista pública (ou vazia, conforme regra de negócio)
    if not current_user:
        return []

    # Usuário logado → apenas seus projetos
    return list_projects(db, owner_id=current_user.id)


# ============================================================
# 🔓 DETALHAR PROJETO → visitante ou usuário
# ============================================================
@router.get("/{project_id}", response_model=ProjectResponse)
def get_project_route(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_current_user_optional),
):
    project = get_project(db, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    # Se estiver logado, valida dono
    if current_user and project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    # Visitante pode visualizar se existir
    return project


# ============================================================
# 🔒 ATUALIZAR PROJETO → exige login
# ============================================================
@router.put("/{project_id}", response_model=ProjectResponse)
def update_project_route(
    project_id: int,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    project = get_project(db, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    return update_project(db, project_id, payload)


# ============================================================
# 🔒 REMOVER PROJETO → exige login
# ============================================================
@router.delete("/{project_id}")
def delete_project_route(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    project = get_project(db, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    delete_project(db, project_id)
    return {"deleted": True}
