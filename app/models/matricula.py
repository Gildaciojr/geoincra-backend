from datetime import datetime
from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.core.database import Base


class Matricula(Base):
    __tablename__ = "matriculas"

    __table_args__ = (
        UniqueConstraint(
            "imovel_id",
            "numero_matricula",
            name="uq_imovel_numero_matricula",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    # 🔗 Relações principais
    imovel_id = Column(
        Integer,
        ForeignKey("imoveis.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    cartorio_id = Column(
        Integer,
        ForeignKey("cartorios.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # ================================
    # DADOS DA MATRÍCULA
    # ================================

    numero_matricula = Column(String(100), nullable=False, index=True)
    livro = Column(String(50), nullable=True)
    folha = Column(String(50), nullable=True)

    comarca = Column(String(150), nullable=True)
    codigo_cartorio = Column(String(50), nullable=True)

    data_abertura = Column(Date, nullable=True)
    data_ultima_atualizacao = Column(Date, nullable=True)

    # Inteiro teor / descrição registral
    inteiro_teor = Column(Text, nullable=True)

    # Caminho do arquivo da matrícula (PDF / imagem)
    arquivo_path = Column(String(512), nullable=True)

    # Situação registral
    status = Column(
        String(50),
        nullable=False,
        default="ATIVA",  # ATIVA | CANCELADA | DESMEMBRADA | UNIFICADA
    )

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
        back_populates="matriculas",
        lazy="joined",
    )

    cartorio = relationship(
        "Cartorio",
        back_populates="matriculas",
        lazy="joined",
    )

    documentos = relationship(
        "Document",
        back_populates="matricula",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Matricula id={self.id} "
            f"numero={self.numero_matricula} "
            f"imovel_id={self.imovel_id} "
            f"status={self.status}>"
        )
