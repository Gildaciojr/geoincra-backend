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
        Index("ix_pagamento_status", "status"),
        Index("ix_pagamento_vencimento", "data_vencimento"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # =========================================================
    # RELAÇÃO COM PROJETO
    # =========================================================
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # =========================================================
    # DADOS FINANCEIROS
    # =========================================================
    descricao = Column(String(255), nullable=False)
    valor = Column(Float, nullable=False)

    # ENTRADA | PARCELA | QUITACAO
    tipo = Column(
        String(30),
        nullable=False,
        default="PARCELA",
    )

    status = Column(
        String(30),
        nullable=False,
        default="PENDENTE",
    )

    modelo = Column(
        String(20),
        nullable=False,
        default="100",                  # modelo padrão
    )

    total = Column(
        Float,
        nullable=False,
        default=0.00,
    )

    data_vencimento = Column(DateTime(timezone=True), nullable=False)
    data_pagamento = Column(DateTime(timezone=True), nullable=True)

    # =========================================================
    # CONTROLE
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
    )

    eventos = relationship(
        "PagamentoEvento",
        back_populates="pagamento",
        cascade="all, delete-orphan",
        lazy="joined",
    )

    parcelas = relationship(
        "ParcelaPagamento",
        back_populates="pagamento",
        cascade="all, delete-orphan",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return (
            f"<Pagamento id={self.id} "
            f"project_id={self.project_id} "
            f"valor={self.valor} "
            f"status={self.status}>"
        )
