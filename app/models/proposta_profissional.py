from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    ForeignKey,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class PropostaProfissional(Base):
    __tablename__ = "propostas_profissionais"

    __table_args__ = (
        UniqueConstraint(
            "project_id",
            "profissional_id",
            name="uq_projeto_profissional_unica",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    # =========================================================
    # 🔗 RELAÇÕES
    # =========================================================
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    profissional_id = Column(
        Integer,
        ForeignKey("profissionais.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # =========================================================
    # STATUS DA PROPOSTA
    # =========================================================
    # ENVIADA | ACEITA | RECUSADA | EXPIRADA | CANCELADA
    status = Column(
        String(30),
        nullable=False,
        default="ENVIADA",
    )

    # =========================================================
    # VALORES / CONDIÇÕES
    # =========================================================
    valor_proposto = Column(Integer, nullable=True)
    prazo_dias = Column(Integer, nullable=True)

    observacoes = Column(Text, nullable=True)

    enviada_em = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    respondida_em = Column(DateTime(timezone=True), nullable=True)

    # =========================================================
    # RELACIONAMENTOS
    # =========================================================
    project = relationship(
        "Project",
        backref="propostas_profissionais",
        lazy="joined",
    )

    profissional = relationship(
        "Profissional",
        backref="propostas_recebidas",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return (
            f"<PropostaProfissional id={self.id} "
            f"project_id={self.project_id} "
            f"profissional_id={self.profissional_id} "
            f"status={self.status}>"
        )
