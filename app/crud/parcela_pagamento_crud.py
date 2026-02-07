from sqlalchemy.orm import Session

from app.models.pagamento import Pagamento
from app.models.parcela_pagamento import ParcelaPagamento
from app.schemas.parcela_pagamento import ParcelaPagamentoCreate, ParcelaPagamentoUpdate
from app.services.pagamento_service import PagamentoService


def criar_parcela_manual(
    db: Session,
    pagamento_id: int,
    data: ParcelaPagamentoCreate,
) -> ParcelaPagamento:
    pagamento = db.query(Pagamento).filter(Pagamento.id == pagamento_id).first()
    if not pagamento:
        raise ValueError("Pagamento não encontrado.")
    if pagamento.status == "CANCELADO":
        raise ValueError("Pagamento cancelado não pode receber parcelas.")

    parcela = ParcelaPagamento(
        pagamento_id=pagamento_id,
        numero=data.numero,
        percentual=data.percentual,
        valor=data.valor,
        vencimento=data.vencimento,
        status=data.status,
        pago_em=data.pago_em,
        forma_pagamento=data.forma_pagamento,
        referencia_interna=data.referencia_interna,
        observacoes=data.observacoes,
    )

    db.add(parcela)
    db.commit()
    db.refresh(parcela)

    PagamentoService.registrar_evento(
        db=db,
        pagamento_id=pagamento_id,
        tipo="PARCELAS_GERADAS",
        descricao="Parcela criada manualmente (modelo CUSTOM).",
        metadata_json={"parcela_id": parcela.id, "numero": parcela.numero, "valor": parcela.valor},
    )

    PagamentoService.recalcular_status_pagamento(db, pagamento_id)
    return parcela


def listar_parcelas(db: Session, pagamento_id: int) -> list[ParcelaPagamento]:
    return (
        db.query(ParcelaPagamento)
        .filter(ParcelaPagamento.pagamento_id == pagamento_id)
        .order_by(ParcelaPagamento.numero.asc())
        .all()
    )


def get_parcela(db: Session, parcela_id: int) -> ParcelaPagamento | None:
    return db.query(ParcelaPagamento).filter(ParcelaPagamento.id == parcela_id).first()


def update_parcela(db: Session, parcela_id: int, data: ParcelaPagamentoUpdate) -> ParcelaPagamento | None:
    parcela = get_parcela(db, parcela_id)
    if not parcela:
        return None

    payload = data.model_dump(exclude_unset=True)
    for field, value in payload.items():
        setattr(parcela, field, value)

    db.commit()
    db.refresh(parcela)

    PagamentoService.recalcular_status_pagamento(db, parcela.pagamento_id)
    return parcela


def marcar_paga(
    db: Session,
    parcela_id: int,
    forma_pagamento: str | None = None,
    observacoes: str | None = None,
    pago_em=None,
) -> ParcelaPagamento:
    return PagamentoService.marcar_parcela_paga(
        db=db,
        parcela_id=parcela_id,
        forma_pagamento=forma_pagamento,
        observacoes=observacoes,
        pago_em=pago_em,
    )
