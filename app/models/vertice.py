from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import relationship

from app.core.database import Base


class Vertice(Base):
    __tablename__ = "vertices"

    id = Column(Integer, primary_key=True, index=True)

    geometria_id = Column(
        Integer,
        ForeignKey("geometrias.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    indice = Column(Integer, nullable=False)

    x = Column(Float, nullable=False)
    y = Column(Float, nullable=False)

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
        back_populates="vertices"
    )

    def __repr__(self):
        return f"<Vertice {self.indice} ({self.x}, {self.y})>"