from datetime import datetime
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class Confrontante(Base):
    __tablename__ = "confrontantes"

    id = Column(Integer, primary_key=True, index=True)

    # 🔗 Relacionamento direto com IMÓVEL (correto para SIGEF / croqui)
    imovel_id = Column(
        Integer,
        ForeignKey("imoveis.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ================================
    # DADOS DO CONFRONTANTE
    # ================================

    # Direção/cardinal no croqui
    # Ex: NORTE, SUL, LESTE, OESTE, NE, NO, SE, SO
    direcao = Column(String(20), nullable=False)

    nome_confrontante = Column(String(255), nullable=True)

    # Matrícula do imóvel confrontante (quando existir)
    matricula_confrontante = Column(String(100), nullable=True)

    # Identificação textual do imóvel confrontante
    identificacao_imovel_confrontante = Column(
        String(512),
        nullable=True,
    )

    # Descrição livre (ex: estrada vicinal, rio, área pública, reserva legal)
    descricao = Column(Text, nullable=True)

    # ================================
    # METADADOS TEMPORAIS
    # ================================

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
        back_populates="confrontantes",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return (
            f"<Confrontante id={self.id} "
            f"direcao={self.direcao} "
            f"imovel_id={self.imovel_id}>"
        )
