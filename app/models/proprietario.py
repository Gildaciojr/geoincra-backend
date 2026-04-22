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


class Proprietario(Base):
    __tablename__ = "proprietarios"

    __table_args__ = (
        Index("ix_proprietario_matricula_id", "matricula_id"),
        Index("ix_proprietario_cpf", "cpf"),
        Index("ix_proprietario_cnpj", "cnpj"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # =========================================================
    # RELAÇÕES
    # =========================================================

    # 🔥 LEGADO (mantido)
    imovel_id = Column(
        Integer,
        ForeignKey("imoveis.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # 🔥 NOVO — vínculo correto
    matricula_id = Column(
        Integer,
        ForeignKey("matriculas.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # =========================================================
    # DADOS DO PROPRIETÁRIO
    # =========================================================

    nome_completo = Column(String(255), nullable=False)

    tipo_pessoa = Column(
        String(20),
        nullable=False,
        default="FISICA",
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
    # CONTROLE REGISTRAL (NOVO)
    # =========================================================

    # 🔥 percentual de posse (ex: 50%, 100%)
    percentual_posse = Column(String(20), nullable=True)

    # 🔥 tipo de vínculo (proprietário, usufrutuário, etc.)
    tipo_vinculo = Column(String(50), nullable=True)

    # 🔥 origem (OCR, manual, integração)
    origem = Column(String(50), nullable=True)

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

    # 🔥 NOVO — vínculo com matrícula
    matricula = relationship(
        "Matricula",
        lazy="joined",
    )

    def __repr__(self) -> str:
        return (
            f"<Proprietario id={self.id} "
            f"nome='{self.nome_completo}' "
            f"imovel_id={self.imovel_id} "
            f"matricula_id={self.matricula_id}>"
        )