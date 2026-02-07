from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Text, Float, String
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

    # GeoJSON bruto (Polygon) - normalmente EPSG:4326
    geojson = Column(Text, nullable=False)

    # Metadados úteis
    epsg_origem = Column(Integer, nullable=False, default=4326)
    epsg_utm = Column(Integer, nullable=True)

    # Cálculos (salvos)
    area_hectares = Column(Float, nullable=True)
    perimetro_m = Column(Float, nullable=True)

    # Identificação opcional
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

    # ================================
    # RELACIONAMENTOS
    # ================================
    imovel = relationship(
        "Imovel",
        back_populates="geometrias",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return f"<Geometria id={self.id} imovel_id={self.imovel_id} epsg={self.epsg_origem}>"
