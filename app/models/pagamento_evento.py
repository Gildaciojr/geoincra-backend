from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class PagamentoEvento(Base):
    __tablename__ = "pagamento_eventos"

    __table_args__ = (
        Index("ix_pagamento_eventos_pagamento_id", "pagamento_id"),
        Index("ix_pagamento_eventos_tipo", "tipo"),
    )

    id = Column(Integer, primary_key=True, index=True)

    pagamento_id = Column(
        Integer,
        ForeignKey("pagamentos.id", ondelete="CASCADE"),
        nullable=False,
    )

    # CRIADO | PARCELAS_GERADAS | PARCELA_PAGA | STATUS_ALTERADO | CANCELADO | OBS_ATUALIZADA
    tipo = Column(String(40), nullable=False)

    descricao = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)

    criado_por_usuario_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    criado_em = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # =========================================================
    # RELACIONAMENTOS
    # =========================================================
    pagamento = relationship(
        "Pagamento",
        back_populates="eventos",
        lazy="joined",
    )

    usuario = relationship(
        "User",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return (
            f"<PagamentoEvento id={self.id} "
            f"pagamento_id={self.pagamento_id} "
            f"tipo={self.tipo}>"
        )
