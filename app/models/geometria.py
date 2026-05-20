from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
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

    documento_origem_id = Column(
        Integer,
        ForeignKey(
            "documents.id",
            ondelete="SET NULL",
        ),
        nullable=True,
        index=True,
    )

    geojson = Column(Text, nullable=False)

    geojson_original = Column(
        Text,
        nullable=True,
    )

    metadata_json = Column(
        Text,
        nullable=True,
    )

    epsg_origem = Column(Integer, nullable=False, default=4326)
    epsg_utm = Column(Integer, nullable=True)

    referencial = Column(
        String(120),
        nullable=True,
    )

    tipo_geometria = Column(
        String(120),
        nullable=True,
    )

    area_hectares = Column(Float, nullable=True)

    score_confianca = Column(
        Integer,
        nullable=True,
    )

    erro_fechamento_metros = Column(
        Float,
        nullable=True,
    )

    perimetro_m = Column(Float, nullable=True)

    reconstruido_por_ocr = Column(
        Integer,
        nullable=False,
        default=0,
    )

    modo_recuperacao = Column(
        Integer,
        nullable=False,
        default=0,
    )

    possui_georreferenciamento_real = Column(
        Integer,
        nullable=False,
        default=1,
    )

    nome = Column(String(120), nullable=True)
    observacoes = Column(Text, nullable=True)

    origem_ocr = Column(
        String(120),
        nullable=True,
        index=True,
    )

    prompt_utilizado = Column(
        String(255),
        nullable=True,
    )

    pipeline_utilizado = Column(
        String(255),
        nullable=True,
        index=True,
    )

    engine_utilizada = Column(
        String(120),
        nullable=True,
    )

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

    documento_origem = relationship(
        "Document",
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
            f"<Geometria "
            f"id={self.id} "
            f"imovel_id={self.imovel_id} "
            f"epsg_origem={self.epsg_origem} "
            f"epsg_utm={self.epsg_utm} "
            f"pipeline={self.pipeline_utilizado} "
            f"ocr={self.origem_ocr}>"
        )