from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    DateTime,
    ForeignKey,
    Index,
    Boolean,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class ParcelaPagamento(Base):
    __tablename__ = "parcelas_pagamento"

    __table_args__ = (
        Index("ix_parcelas_pagamento_pagamento_id", "pagamento_id"),
        Index("ix_parcelas_pagamento_status", "status"),
        Index("ix_parcelas_pagamento_vencimento", "vencimento"),
        Index("ix_parcelas_pagamento_ordem", "ordem"),
    )

    id = Column(Integer, primary_key=True, index=True)

    pagamento_id = Column(
        Integer,
        ForeignKey("pagamentos.id", ondelete="CASCADE"),
        nullable=False,
    )

    # 🔢 Ordem lógica da parcela (1, 2, 3...)
    ordem = Column(Integer, nullable=False)

    percentual = Column(Float, nullable=False)
    valor = Column(Float, nullable=False)

    vencimento = Column(DateTime(timezone=True), nullable=True)

    status = Column(
        String(20),
        nullable=False,
        default="PENDENTE",  # PENDENTE | PAGO | ATRASADA | CANCELADA
    )

    # 🔓 Liberação automática baseada no progresso técnico
    liberada = Column(Boolean, nullable=False, default=False)
    liberada_em = Column(DateTime(timezone=True), nullable=True)

    pago_em = Column(DateTime(timezone=True), nullable=True)
    forma_pagamento = Column(String(50), nullable=True)
    referencia_interna = Column(String(120), nullable=True)
    observacoes = Column(String(512), nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    pagamento = relationship(
        "Pagamento",
        back_populates="parcelas",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return (
            f"<ParcelaPagamento id={self.id} "
            f"pagamento_id={self.pagamento_id} "
            f"ordem={self.ordem} status={self.status} "
            f"liberada={self.liberada}>"
        )
