from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    Float,
    String,
    DateTime,
    ForeignKey,
    Boolean,
    Index,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Pagamento(Base):
    __tablename__ = "pagamentos"

    __table_args__ = (
        Index("ix_pagamento_project", "project_id"),
        Index("ix_pagamento_proposal", "proposal_id"),
        Index("ix_pagamento_status", "status"),
        Index("ix_pagamento_vencimento", "data_vencimento"),
        Index("ix_pagamento_modelo", "modelo"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # =========================================================
    # RELAÇÕES PRINCIPAIS
    # =========================================================
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 🔗 VÍNCULO COM A PROPOSTA (ACEITE FORMAL)
    proposal_id = Column(
        Integer,
        ForeignKey("proposals.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # =========================================================
    # DADOS FINANCEIROS
    # =========================================================
    descricao = Column(String(255), nullable=False)

    # valor operacional (mantido por compatibilidade)
    valor = Column(Float, nullable=False)

    # valor total do pagamento (base de cálculo das parcelas)
    total = Column(
        Float,
        nullable=False,
        default=0.00,
    )

    # ENTRADA | PARCELA | QUITACAO
    tipo = Column(
        String(30),
        nullable=False,
        default="PARCELA",
    )

    # PENDENTE | PARCIAL | PAGO | ATRASADO | CANCELADO
    status = Column(
        String(30),
        nullable=False,
        default="PENDENTE",
    )

    # 100 | 50_50 | 20_30_50 | CUSTOM
    modelo = Column(
        String(20),
        nullable=False,
        default="100",
    )

    data_vencimento = Column(DateTime(timezone=True), nullable=False)
    data_pagamento = Column(DateTime(timezone=True), nullable=True)

    # =========================================================
    # CONTROLE DE FLUXO
    # =========================================================
    bloqueia_fluxo = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    criado_automaticamente = Column(
        Boolean,
        nullable=False,
        default=True,
    )

    # =========================================================
    # METADADOS
    # =========================================================
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

    # =========================================================
    # RELACIONAMENTOS
    # =========================================================
    project = relationship(
        "Project",
        backref="pagamentos",
        lazy="joined",
        passive_deletes=True,
    )

    proposal = relationship(
        "Proposal",
        lazy="joined",
    )

    eventos = relationship(
        "PagamentoEvento",
        back_populates="pagamento",
        cascade="all, delete-orphan",
        lazy="joined",
        passive_deletes=True,
    )

    parcelas = relationship(
        "ParcelaPagamento",
        back_populates="pagamento",
        cascade="all, delete-orphan",
        lazy="joined",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return (
            f"<Pagamento id={self.id} "
            f"project_id={self.project_id} "
            f"proposal_id={self.proposal_id} "
            f"total={self.total} "
            f"status={self.status}>"
        )
