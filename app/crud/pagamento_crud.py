from sqlalchemy.orm import Session
from datetime import datetime

from app.models.pagamento import Pagamento
from app.models.project import Project
from app.schemas.pagamento import PagamentoCreate, PagamentoUpdate


# =========================================================
# CREATE
# =========================================================
def create_pagamento(
    db: Session,
    project_id: int,
    data: PagamentoCreate,
) -> Pagamento:

    project = db.query(Project).filter(Project.id == project_id).first()
    if not project:
        raise ValueError("Projeto não encontrado.")

    obj = Pagamento(
        project_id=project_id,
        descricao=data.descricao,
        valor=data.valor,
        total=data.valor,
        modelo=data.modelo,
        tipo=data.tipo,
        status=data.status.upper(),
        data_vencimento=data.data_vencimento,
        bloqueia_fluxo=data.bloqueia_fluxo,
        criado_automaticamente=False,
    )

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


# =========================================================
# LIST POR PROJETO
# =========================================================
def list_pagamentos_by_project(
    db: Session,
    project_id: int,
) -> list[Pagamento]:
    return (
        db.query(Pagamento)
        .filter(Pagamento.project_id == project_id)
        .order_by(Pagamento.id.asc())
        .all()
    )


# =========================================================
# GET
# =========================================================
def get_pagamento(
    db: Session,
    pagamento_id: int,
) -> Pagamento | None:
    return (
        db.query(Pagamento)
        .filter(Pagamento.id == pagamento_id)
        .first()
    )


# =========================================================
# UPDATE
# =========================================================
def update_pagamento(
    db: Session,
    pagamento_id: int,
    payload: PagamentoUpdate,
) -> Pagamento | None:

    pagamento = get_pagamento(db, pagamento_id)
    if not pagamento:
        return None

    data = payload.model_dump(exclude_unset=True)

    if "status" in data:
        pagamento.status = data["status"].upper()

        if pagamento.status == "PAGO" and not pagamento.data_pagamento:
            pagamento.data_pagamento = datetime.utcnow()

    if "valor" in data:
        pagamento.valor = float(data["valor"])
        pagamento.total = float(data["valor"])

    if "modelo" in data:
        pagamento.modelo = data["modelo"]

    if "bloqueia_fluxo" in data:
        pagamento.bloqueia_fluxo = data["bloqueia_fluxo"]

    pagamento.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(pagamento)
    return pagamento


# =========================================================
# CANCELAR
# =========================================================
def cancelar_pagamento(
    db: Session,
    pagamento_id: int,
) -> bool:

    pagamento = get_pagamento(db, pagamento_id)

    if not pagamento:
        return False

    pagamento.status = "CANCELADO"
    pagamento.updated_at = datetime.utcnow()

    db.commit()
    return True
