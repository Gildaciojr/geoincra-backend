from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from app.core.database import Base


class Template(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)

    nome = Column(String(255), nullable=False)
    descricao = Column(Text, nullable=True)

    # cartorio | sigef | usucapiao | contratos
    categoria = Column(String(80), nullable=False)

    versao = Column(String(20), nullable=True)

    stored_filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)

    file_path = Column(String(512), nullable=False)

    ativo = Column(Boolean, nullable=False, default=True)

    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Template id={self.id} nome={self.nome} categoria={self.categoria}>"
