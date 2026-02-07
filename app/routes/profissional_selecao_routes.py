# app/routes/profissional_selecao_routes.py

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db

from app.schemas.profissional_selecao import (
    ProfissionalSelecaoCreate,
    ProfissionalSelecaoManualCreate,
    ProfissionalSelecaoResponse,
)

from app.crud.profissional_selecao_crud import (
    get_selecao_atual,
    list_historico_selecoes,
)

from app.services.profissional_selecao_service import ProfissionalSelecaoService

router = APIRouter()


# =========================================================
# AUTO: selecionar melhor profissional para o projeto
# POST /projects/{project_id}/profissionais/selecionar/auto
# =========================================================
@router.post(
    "/projects/{project_id}/profissionais/selecionar/auto",
    response_model=ProfissionalSelecaoResponse,
)
def selecionar_auto(
    project_id: int,
    payload: ProfissionalSelecaoCreate,
    db: Session = Depends(get_db),
):
    try:
        return ProfissionalSelecaoService.selecionar_melhor_profissional(
            db=db,
            project_id=project_id,
            automatico=True,
            escolhido_por_user_id=None,  # até autenticação
            observacao=payload.observacoes,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =========================================================
# MANUAL: selecionar profissional específico
# POST /projects/{project_id}/profissionais/selecionar/manual
# =========================================================
@router.post(
    "/projects/{project_id}/profissionais/selecionar/manual",
    response_model=ProfissionalSelecaoResponse,
)
def selecionar_manual(
    project_id: int,
    payload: ProfissionalSelecaoManualCreate,
    db: Session = Depends(get_db),
):
    try:
        return ProfissionalSelecaoService.selecionar_profissional_manual(
            db=db,
            project_id=project_id,
            profissional_id=payload.profissional_id,
            escolhido_por_user_id=None,  # até autenticação
            observacao=payload.observacoes,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


# =========================================================
# GET seleção atual do projeto
# GET /projects/{project_id}/profissionais/selecionado
# =========================================================
@router.get(
    "/projects/{project_id}/profissionais/selecionado",
    response_model=ProfissionalSelecaoResponse,
)
def get_atual(project_id: int, db: Session = Depends(get_db)):
    sel = get_selecao_atual(db, project_id)
    if not sel:
        raise HTTPException(status_code=404, detail="Nenhuma seleção encontrada para este projeto.")
    return sel


# =========================================================
# LIST histórico de seleções do projeto
# GET /projects/{project_id}/profissionais/selecoes
# =========================================================
@router.get(
    "/projects/{project_id}/profissionais/selecoes",
    response_model=list[ProfissionalSelecaoResponse],
)
def list_historico(project_id: int, db: Session = Depends(get_db)):
    return list_historico_selecoes(db, project_id)
