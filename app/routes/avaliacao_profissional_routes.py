from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.project import Project
from app.schemas.avaliacao_profissional import (
    AvaliacaoProfissionalCreate,
    AvaliacaoProfissionalResponse,
)
from app.crud.avaliacao_profissional_crud import (
    criar_avaliacao,
    listar_avaliacoes_profissional,
)

router = APIRouter()


def _check_project_owner(db: Session, project_id: int, user_id: int):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == user_id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    return project


# =========================================================
# CREATE (somente dono do projeto)
# =========================================================
@router.post(
    "/projects/{project_id}/avaliacoes/",
    response_model=AvaliacaoProfissionalResponse,
)
def criar_avaliacao_route(
    project_id: int,
    payload: AvaliacaoProfissionalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_project_owner(db, project_id, current_user.id)

    try:
        return criar_avaliacao(db, project_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =========================================================
# LIST (público – OK)
# =========================================================
@router.get(
    "/profissionais/{profissional_id}/avaliacoes/",
    response_model=list[AvaliacaoProfissionalResponse],
)
def listar_avaliacoes_profissional_route(
    profissional_id: int,
    db: Session = Depends(get_db),
):
    return listar_avaliacoes_profissional(db, profissional_id)
