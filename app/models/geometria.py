from datetime import datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class Geometria(Base):
    __tablename__ = "geometrias"

    id = Column(Integer, primary_key=True, index=True)

    imovel_id = Column(
        Integer,
        ForeignKey("imoveis.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    geojson = Column(Text, nullable=False)

    epsg_origem = Column(Integer, nullable=False, default=4326)
    epsg_utm = Column(Integer, nullable=True)

    area_hectares = Column(Float, nullable=True)
    perimetro_m = Column(Float, nullable=True)

    nome = Column(String(120), nullable=True)
    observacoes = Column(Text, nullable=True)

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

    imovel = relationship(
        "Imovel",
        back_populates="geometrias",
        lazy="joined",
    )

    vertices = relationship(
        "Vertice",
        back_populates="geometria",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Vertice.indice"
    )

    segmentos = relationship(
        "Segmento",
        back_populates="geometria",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Segmento.indice"
    )

    def __repr__(self) -> str:
        return (
            f"<Geometria id={self.id} "
            f"imovel_id={self.imovel_id} "
            f"epsg_origem={self.epsg_origem} "
            f"epsg_utm={self.epsg_utm}>"
        )