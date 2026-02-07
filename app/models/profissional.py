from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Boolean,
    Text,
    Float,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Profissional(Base):
    __tablename__ = "profissionais"

    __table_args__ = (
        UniqueConstraint("cpf", name="uq_profissional_cpf"),
        UniqueConstraint("cnpj", name="uq_profissional_cnpj"),
        Index("ix_profissional_ativo", "ativo"),
        Index("ix_profissional_crea", "crea"),
    )

    id = Column(Integer, primary_key=True, index=True)

    nome_completo = Column(String(255), nullable=False)
    tipo_pessoa = Column(String(20), nullable=False, default="FISICA")

    cpf = Column(String(14), nullable=True)
    cnpj = Column(String(18), nullable=True)

    crea = Column(String(50), nullable=True)
    uf_crea = Column(String(2), nullable=True)
    especialidades = Column(Text, nullable=True)

    telefone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)

    ativo = Column(Boolean, nullable=False, default=True)

    rating_medio = Column(Float, nullable=False, default=0.0)
    total_servicos = Column(Integer, nullable=False, default=0)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # ✅ ÚNICO relacionamento de avaliações
    avaliacoes = relationship(
        "AvaliacaoProfissional",
        back_populates="profissional",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<Profissional id={self.id} nome='{self.nome_completo}'>"
