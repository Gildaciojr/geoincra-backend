from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.project import Project
from app.schemas.pagamento import PagamentoCreate, PagamentoUpdate, PagamentoResponse
from app.schemas.parcela_pagamento import ParcelaPagamentoResponse
from app.schemas.pagamento_evento import PagamentoEventoResponse

from app.crud.pagamento_crud import (
    create_pagamento,
    list_pagamentos_by_project,
    get_pagamento,
    update_pagamento,
    cancelar_pagamento,
)
from app.crud.parcela_pagamento_crud import listar_parcelas
from app.crud.pagamento_evento_crud import listar_eventos
from app.services.pagamento_service import PagamentoService

router = APIRouter()


# =========================================================
# HELPERS
# =========================================================
def _check_project_owner(db: Session, project_id: int, user_id: int):
    project = db.query(Project).filter(
        Project.id == project_id,
        Project.owner_id == user_id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    return project


def _check_pagamento_owner(db: Session, pagamento_id: int, user_id: int):
    pagamento = get_pagamento(db, pagamento_id)
    if not pagamento:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")

    _check_project_owner(db, pagamento.project_id, user_id)
    return pagamento


# =========================================================
# CREATE
# =========================================================
@router.post(
    "/projects/{project_id}/pagamentos/",
    response_model=PagamentoResponse,
)
def create_pagamento_route(
    project_id: int,
    payload: PagamentoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_project_owner(db, project_id, current_user.id)
    return create_pagamento(db, project_id, payload)


# =========================================================
# LIST POR PROJETO
# =========================================================
@router.get(
    "/projects/{project_id}/pagamentos/",
    response_model=list[PagamentoResponse],
)
def list_pagamentos_route(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_project_owner(db, project_id, current_user.id)
    return list_pagamentos_by_project(db, project_id)


# =========================================================
# GET
# =========================================================
@router.get(
    "/pagamentos/{pagamento_id}",
    response_model=PagamentoResponse,
)
def get_pagamento_route(
    pagamento_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _check_pagamento_owner(db, pagamento_id, current_user.id)


# =========================================================
# UPDATE
# =========================================================
@router.put(
    "/pagamentos/{pagamento_id}",
    response_model=PagamentoResponse,
)
def update_pagamento_route(
    pagamento_id: int,
    payload: PagamentoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_pagamento_owner(db, pagamento_id, current_user.id)
    pagamento = update_pagamento(db, pagamento_id, payload)
    return pagamento


# =========================================================
# CANCELAR
# =========================================================
@router.delete("/pagamentos/{pagamento_id}")
def cancelar_pagamento_route(
    pagamento_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_pagamento_owner(db, pagamento_id, current_user.id)
    cancelar_pagamento(db, pagamento_id)
    return {"cancelado": True}


# =========================================================
# GERAR PARCELAS PADRÃO
# =========================================================
@router.post(
    "/pagamentos/{pagamento_id}/gerar-parcelas",
    response_model=list[ParcelaPagamentoResponse],
)
def gerar_parcelas_route(
    pagamento_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    pagamento = _check_pagamento_owner(db, pagamento_id, current_user.id)
    return PagamentoService.gerar_parcelas_padrao(db, pagamento)


# =========================================================
# LISTAR PARCELAS
# =========================================================
@router.get(
    "/pagamentos/{pagamento_id}/parcelas",
    response_model=list[ParcelaPagamentoResponse],
)
def listar_parcelas_route(
    pagamento_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_pagamento_owner(db, pagamento_id, current_user.id)
    return listar_parcelas(db, pagamento_id)


# =========================================================
# EVENTOS / HISTÓRICO FINANCEIRO
# =========================================================
@router.get(
    "/pagamentos/{pagamento_id}/eventos",
    response_model=list[PagamentoEventoResponse],
)
def listar_eventos_route(
    pagamento_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_pagamento_owner(db, pagamento_id, current_user.id)
    return listar_eventos(db, pagamento_id)


# =========================================================
# LIBERAÇÃO CONDICIONAL
# =========================================================
@router.get("/pagamentos/{pagamento_id}/liberacao")
def liberacao_route(
    pagamento_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_pagamento_owner(db, pagamento_id, current_user.id)
    return PagamentoService.liberar_condicional(db, pagamento_id)
