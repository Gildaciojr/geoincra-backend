from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    Float,
    DateTime,
    Boolean,
    ForeignKey,
    Index,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class ProfissionalRanking(Base):
    __tablename__ = "profissional_rankings"

    __table_args__ = (
        UniqueConstraint(
            "profissional_id",
            name="uq_profissional_ranking_profissional",
        ),
        Index("ix_prof_ranking_score", "score"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # =========================================================
    # RELAÇÃO
    # =========================================================
    profissional_id = Column(
        Integer,
        ForeignKey("profissionais.id", ondelete="CASCADE"),
        nullable=False,
    )

    # =========================================================
    # MÉTRICAS DE RANKING
    # =========================================================
    score = Column(Float, nullable=False)
    avaliacao_media = Column(Float, nullable=True)
    total_projetos = Column(Integer, nullable=False, default=0)

    ativo = Column(Boolean, nullable=False, default=True)

    calculado_em = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # =========================================================
    # RELACIONAMENTOS
    # =========================================================
    profissional = relationship(
        "Profissional",
        backref="ranking",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return (
            f"<ProfissionalRanking profissional_id={self.profissional_id} "
            f"score={self.score}>"
        )
