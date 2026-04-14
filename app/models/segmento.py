from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.core.database import Base


class Segmento(Base):
    __tablename__ = "segmentos"

    id = Column(Integer, primary_key=True, index=True)

    geometria_id = Column(
        Integer,
        ForeignKey("geometrias.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    indice = Column(Integer, nullable=False)

    distancia = Column(Float, nullable=False)
    azimute = Column(Float, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    # =========================================================
    # RELACIONAMENTO
    # =========================================================
    geometria = relationship(
        "Geometria",
        back_populates="segmentos"
    )

    def __repr__(self):
        return f"<Segmento {self.indice} dist={self.distancia} az={self.azimute}>"