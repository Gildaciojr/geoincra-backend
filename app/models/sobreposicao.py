# app/models/sobreposicao.py

from datetime import datetime
from sqlalchemy import Column, Integer, Float, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from app.core.database import Base


class Sobreposicao(Base):
    __tablename__ = "sobreposicoes"

    id = Column(Integer, primary_key=True, index=True)

    geometria_base_id = Column(
        Integer,
        ForeignKey("geometrias.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    geometria_afetada_id = Column(
        Integer,
        ForeignKey("geometrias.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    area_sobreposta_ha = Column(Float, nullable=False)
    percentual_sobreposicao = Column(Float, nullable=False)

    tipo = Column(
        String(50),
        nullable=False,
        comment="SIGEF | CAR | IMOVEL_INTERNO",
    )

    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    geometria_base = relationship(
        "Geometria",
        foreign_keys=[geometria_base_id],
        lazy="joined",
    )

    geometria_afetada = relationship(
        "Geometria",
        foreign_keys=[geometria_afetada_id],
        lazy="joined",
    )
