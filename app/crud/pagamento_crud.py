from sqlalchemy.orm import Session
from datetime import datetime

from app.models.pagamento import Pagamento
from app.models.project import Project
from app.schemas.pagamento import PagamentoCreate, PagamentoUpdate
from app.services.pagamento_service import PagamentoService


# =========================================================
# 🔒 STATUS VÁLIDOS
# =========================================================
STATUS_VALIDOS = [
    "PENDENTE",
    "PARCIAL",
    "PAGO",
    "ATRASADO",
    "CANCELADO",
]


# =========================================================
# CREATE
# =========================================================
def create_pagamento(
    db: Session,
    project_id: int,
    data: PagamentoCreate,
) -> Pagamento:

    try:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError("Projeto não encontrado.")

        status = data.status.upper()

        if status not in STATUS_VALIDOS:
            raise ValueError(f"Status inválido: {status}")

        descricao = data.descricao.strip()

        obj = Pagamento(
            project_id=project_id,
            descricao=descricao,
            valor=float(data.valor),

            # ⚠️ FUTURO: calcular baseado nas parcelas
            total=float(data.valor),

            modelo=data.modelo,
            tipo=data.tipo,
            status=status,
            data_vencimento=data.data_vencimento,
            bloqueia_fluxo=data.bloqueia_fluxo,
            criado_automaticamente=False,
        )

        db.add(obj)
        db.commit()
        db.refresh(obj)

        # 🔥 registrar evento inicial
        PagamentoService.registrar_evento(
            db=db,
            pagamento_id=obj.id,
            tipo="CRIADO",
            descricao="Pagamento criado manualmente.",
        )

        return obj

    except Exception as e:
        db.rollback()
        raise e


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

    try:
        pagamento = get_pagamento(db, pagamento_id)
        if not pagamento:
            return None

        data = payload.model_dump(exclude_unset=True)

        if "status" in data:
            status = data["status"].upper()

            if status not in STATUS_VALIDOS:
                raise ValueError(f"Status inválido: {status}")

            pagamento.status = status

            if status == "PAGO" and not pagamento.data_pagamento:
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

        # 🔥 registrar evento
        PagamentoService.registrar_evento(
            db=db,
            pagamento_id=pagamento.id,
            tipo="STATUS_ALTERADO",
            descricao=f"Status atualizado para {pagamento.status}",
        )

        return pagamento

    except Exception as e:
        db.rollback()
        raise e


# =========================================================
# CANCELAR
# =========================================================
def cancelar_pagamento(
    db: Session,
    pagamento_id: int,
) -> bool:

    try:
        pagamento = get_pagamento(db, pagamento_id)

        if not pagamento:
            return False

        pagamento.status = "CANCELADO"
        pagamento.updated_at = datetime.utcnow()

        db.commit()

        PagamentoService.registrar_evento(
            db=db,
            pagamento_id=pagamento.id,
            tipo="CANCELADO",
            descricao="Pagamento cancelado manualmente.",
        )

        return True

    except Exception:
        db.rollback()
        raise