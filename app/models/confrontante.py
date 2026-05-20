from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class Confrontante(Base):
    __tablename__ = "confrontantes"

    __table_args__ = (
        Index("ix_confrontantes_imovel_id", "imovel_id"),
        Index("ix_confrontantes_geometria_id", "geometria_id"),
        Index("ix_confrontantes_direcao_normalizada", "direcao_normalizada"),
        Index("ix_confrontantes_ordem_segmento", "ordem_segmento"),
        # 🔥 novo índice para vínculo futuro
        Index("ix_confrontantes_matricula_id", "matricula_id"),
        Index("ix_confrontantes_hash_segmento", "hash_segmento"),
        Index("ix_confrontantes_origem_ocr", "origem_ocr"),
        Index("ix_confrontantes_pipeline_utilizado", "pipeline_utilizado"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # =========================================================
    # RELACIONAMENTOS PRINCIPAIS
    # =========================================================
    imovel_id = Column(
        Integer,
        ForeignKey("imoveis.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    geometria_id = Column(
        Integer,
        ForeignKey("geometrias.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # 🔥 NOVO — vínculo estruturado com matrícula real
    matricula_id = Column(
        Integer,
        ForeignKey("matriculas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # =========================================================
    # POSICIONAMENTO TÉCNICO
    # =========================================================
    direcao = Column(
        String(20),
        nullable=False,
    )

    direcao_normalizada = Column(
        String(10),
        nullable=True,
        index=True,
    )

    ordem_segmento = Column(
        Integer,
        nullable=True,
        index=True,
    )

    hash_segmento = Column(
        String(255),
        nullable=True,
        index=True,
    )

    lado_label = Column(
        String(30),
        nullable=True,
    )

    vertice_inicial = Column(
        String(100),
        nullable=True,
    )

    vertice_final = Column(
        String(100),
        nullable=True,
    )

    distancia_metros = Column(
        String(50),
        nullable=True,
    )

    azimute = Column(
        String(50),
        nullable=True,
    )

    # =========================================================
    # DADOS DO CONFRONTANTE
    # =========================================================
    nome_confrontante = Column(
        String(255),
        nullable=True,
    )

    # 🔥 MANTIDO (legado)
    matricula_confrontante = Column(
        String(100),
        nullable=True,
    )

    identificacao_imovel_confrontante = Column(
        String(512),
        nullable=True,
    )

    descricao = Column(
        Text,
        nullable=True,
    )

    observacoes = Column(
        Text,
        nullable=True,
    )

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
    )

    engine_utilizada = Column(
        String(120),
        nullable=True,
    )

    # 🔥 NOVOS CAMPOS (sem quebrar nada)
    tipo = Column(
        String(50),
        nullable=True,
    )

    score_confianca = Column(
        Integer,
        nullable=True,
    )

    validado_manualmente = Column(
        Integer,
        nullable=False,
        default=0,
    )

    lote = Column(
        String(50),
        nullable=True,
    )

    gleba = Column(
        String(50),
        nullable=True,
    )

    confrontante_tecnico = Column(
        Integer,
        nullable=False,
        default=1,
    )

    confrontante_auxiliar = Column(
        Integer,
        nullable=False,
        default=0,
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
    # RELACIONAMENTOS ORM
    # =========================================================
    imovel = relationship(
        "Imovel",
        back_populates="confrontantes",
        lazy="joined",
    )

    geometria = relationship(
        "Geometria",
        lazy="joined",
    )

    # 🔥 novo relacionamento
    matricula = relationship(
        "Matricula",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return (
            f"<Confrontante "
            f"id={self.id} "
            f"imovel_id={self.imovel_id} "
            f"geometria_id={self.geometria_id} "
            f"matricula_id={self.matricula_id} "
            f"direcao={self.direcao} "
            f"ordem_segmento={self.ordem_segmento} "
            f"origem_ocr={self.origem_ocr} "
            f"pipeline={self.pipeline_utilizado}>"
        )
