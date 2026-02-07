from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.projeto_profissional import (
    ProjetoProfissionalCreate,
    ProjetoProfissionalUpdate,
    ProjetoProfissionalResponse,
)
from app.crud.projeto_profissional_crud import (
    vincular_profissional_ao_projeto,
    obter_profissional_ativo,
    atualizar_status_execucao,
)

router = APIRouter()


@router.post(
    "/projects/{project_id}/profissional",
    response_model=ProjetoProfissionalResponse,
)
def vincular_profissional(
    project_id: int,
    payload: ProjetoProfissionalCreate,
    db: Session = Depends(get_db),
):
    try:
        return vincular_profissional_ao_projeto(db, project_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/projects/{project_id}/profissional",
    response_model=ProjetoProfissionalResponse,
)
def obter_profissional_em_execucao(
    project_id: int,
    db: Session = Depends(get_db),
):
    vinculo = obter_profissional_ativo(db, project_id)
    if not vinculo:
        raise HTTPException(
            status_code=404,
            detail="Nenhum profissional ativo no projeto.",
        )
    return vinculo


@router.put(
    "/projetos-profissionais/{vinculo_id}",
    response_model=ProjetoProfissionalResponse,
)
def atualizar_execucao(
    vinculo_id: int,
    payload: ProjetoProfissionalUpdate,
    db: Session = Depends(get_db),
):
    vinculo = atualizar_status_execucao(db, vinculo_id, payload)
    if not vinculo:
        raise HTTPException(status_code=404, detail="Vínculo não encontrado.")
    return vinculo
