from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.pagamento import Pagamento

from app.schemas.parcela_pagamento import (
    ParcelaPagamentoCreate,
    ParcelaPagamentoUpdate,
    ParcelaPagamentoResponse,
    MarcarParcelaPagaRequest,
)

from app.crud.parcela_pagamento_crud import (
    criar_parcela_manual,
    listar_parcelas,
    get_parcela,
    update_parcela,
    marcar_paga,
)

router = APIRouter()


# =========================================================
# HELPERS (SECURITY / OWNERSHIP)
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
    pagamento = db.query(Pagamento).filter(Pagamento.id == pagamento_id).first()
    if not pagamento:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")

    _check_project_owner(db, pagamento.project_id, user_id)
    return pagamento


def _check_parcela_owner(db: Session, parcela_id: int, user_id: int):
    parcela = get_parcela(db, parcela_id)
    if not parcela:
        raise HTTPException(status_code=404, detail="Parcela não encontrada.")

    # Normalmente parcela tem pagamento_id (FK). Se o seu model usar outro nome, me avise.
    pagamento_id = getattr(parcela, "pagamento_id", None)
    if pagamento_id is None:
        # fallback defensivo (não deveria acontecer)
        raise HTTPException(status_code=400, detail="Parcela sem pagamento vinculado.")

    _check_pagamento_owner(db, pagamento_id, user_id)
    return parcela


# =========================================================
# CREATE MANUAL (CUSTOM)
# =========================================================
@router.post(
    "/pagamentos/{pagamento_id}/parcelas/",
    response_model=ParcelaPagamentoResponse,
)
def criar_parcela_manual_route(
    pagamento_id: int,
    payload: ParcelaPagamentoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_pagamento_owner(db, pagamento_id, current_user.id)

    try:
        return criar_parcela_manual(db, pagamento_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =========================================================
# LIST
# =========================================================
@router.get(
    "/pagamentos/{pagamento_id}/parcelas/",
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
# GET
# =========================================================
@router.get(
    "/parcelas/{parcela_id}",
    response_model=ParcelaPagamentoResponse,
)
def get_parcela_route(
    parcela_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _check_parcela_owner(db, parcela_id, current_user.id)


# =========================================================
# UPDATE
# =========================================================
@router.put(
    "/parcelas/{parcela_id}",
    response_model=ParcelaPagamentoResponse,
)
def update_parcela_route(
    parcela_id: int,
    payload: ParcelaPagamentoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_parcela_owner(db, parcela_id, current_user.id)

    parcela = update_parcela(db, parcela_id, payload)
    if not parcela:
        raise HTTPException(status_code=404, detail="Parcela não encontrada.")
    return parcela


# =========================================================
# MARCAR COMO PAGA
# =========================================================
@router.post(
    "/parcelas/{parcela_id}/pagar",
    response_model=ParcelaPagamentoResponse,
)
def pagar_parcela_route(
    parcela_id: int,
    payload: MarcarParcelaPagaRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_parcela_owner(db, parcela_id, current_user.id)

    try:
        return marcar_paga(
            db=db,
            parcela_id=parcela_id,
            forma_pagamento=payload.forma_pagamento,
            observacoes=payload.observacoes,
            pago_em=payload.pago_em,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
