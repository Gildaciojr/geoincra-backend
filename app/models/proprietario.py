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


class Proprietario(Base):
    __tablename__ = "proprietarios"

    id = Column(Integer, primary_key=True, index=True)

    # =========================================================
    # 🔗 RELAÇÃO DIRETA COM IMÓVEL
    # =========================================================
    imovel_id = Column(
        Integer,
        ForeignKey("imoveis.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # =========================================================
    # DADOS DO PROPRIETÁRIO
    # =========================================================

    nome_completo = Column(String(255), nullable=False)

    tipo_pessoa = Column(
        String(20),
        nullable=False,
        default="FISICA",  # FISICA | JURIDICA
    )

    cpf = Column(String(14), nullable=True, index=True)
    cnpj = Column(String(18), nullable=True, index=True)

    rg = Column(String(50), nullable=True)
    orgao_emissor = Column(String(50), nullable=True)

    estado_civil = Column(String(50), nullable=True)
    profissao = Column(String(120), nullable=True)

    nacionalidade = Column(String(80), nullable=True)

    # =========================================================
    # ENDEREÇO
    # =========================================================

    endereco = Column(Text, nullable=True)
    municipio = Column(String(120), nullable=True)
    estado = Column(String(2), nullable=True)
    cep = Column(String(15), nullable=True)

    # =========================================================
    # CONTATO
    # =========================================================

    telefone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)

    # =========================================================
    # OBSERVAÇÕES LEGAIS
    # =========================================================

    observacoes = Column(Text, nullable=True)

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
    # RELACIONAMENTOS
    # =========================================================

    imovel = relationship(
        "Imovel",
        back_populates="proprietarios",
        lazy="joined",
    )

    # =========================================================
    # REPRESENTAÇÃO
    # =========================================================

    def __repr__(self) -> str:
        return (
            f"<Proprietario id={self.id} "
            f"nome='{self.nome_completo}' "
            f"imovel_id={self.imovel_id}>"
        )
