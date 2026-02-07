from sqlalchemy.orm import Session

from app.models.pagamento_evento import PagamentoEvento


def listar_eventos(db: Session, pagamento_id: int) -> list[PagamentoEvento]:
    return (
        db.query(PagamentoEvento)
        .filter(PagamentoEvento.pagamento_id == pagamento_id)
        .order_by(PagamentoEvento.criado_em.desc())
        .all()
    )
