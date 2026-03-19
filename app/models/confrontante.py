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
    )

    id = Column(Integer, primary_key=True, index=True)

    # =========================================================
    # RELACIONAMENTOS PRINCIPAIS
    # =========================================================
    # Imóvel ao qual o confrontante pertence
    imovel_id = Column(
        Integer,
        ForeignKey("imoveis.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Geometria usada para associar o confrontante ao perímetro analisado
    geometria_id = Column(
        Integer,
        ForeignKey("geometrias.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # =========================================================
    # DADOS DE POSICIONAMENTO / VÍNCULO TÉCNICO
    # =========================================================
    # Direção original vinda do OCR / usuário
    # Ex.: NORTE, SUL, LESTE, OESTE, NE, NO, SE, SO
    direcao = Column(
        String(20),
        nullable=False,
    )

    # Direção normalizada técnica
    # Ex.: N, S, E, W, NE, NW, SE, SW
    direcao_normalizada = Column(
        String(10),
        nullable=True,
        index=True,
    )

    # Ordem do segmento/lado dentro do polígono
    # Ex.: 1, 2, 3, 4...
    ordem_segmento = Column(
        Integer,
        nullable=True,
        index=True,
    )

    # Rótulo visual/técnico do lado
    # Ex.: LADO_01, LADO_02...
    lado_label = Column(
        String(30),
        nullable=True,
    )

    # =========================================================
    # DADOS DO CONFRONTANTE
    # =========================================================
    nome_confrontante = Column(
        String(255),
        nullable=True,
    )

    # Matrícula do imóvel confrontante, quando existir
    matricula_confrontante = Column(
        String(100),
        nullable=True,
    )

    # Identificação textual do imóvel confrontante
    identificacao_imovel_confrontante = Column(
        String(512),
        nullable=True,
    )

    # Descrição livre
    # Ex.: estrada vicinal, rio, área pública, reserva legal
    descricao = Column(
        Text,
        nullable=True,
    )

    # Observação técnica complementar
    observacoes = Column(
        Text,
        nullable=True,
    )

    # =========================================================
    # METADADOS TEMPORAIS
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

    def __repr__(self) -> str:
        return (
            f"<Confrontante id={self.id} "
            f"imovel_id={self.imovel_id} "
            f"geometria_id={self.geometria_id} "
            f"direcao={self.direcao} "
            f"direcao_normalizada={self.direcao_normalizada} "
            f"ordem_segmento={self.ordem_segmento}>"
        )