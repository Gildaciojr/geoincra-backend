from datetime import datetime
from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class Cartorio(Base):
    __tablename__ = "cartorios"

    id = Column(Integer, primary_key=True, index=True)

    nome = Column(String(255), nullable=False, index=True)
    tipo = Column(String(100), nullable=True)

    cns = Column(String(20), nullable=True, unique=True, index=True)

    endereco = Column(Text, nullable=True)
    telefone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)

    municipio = Column(String(120), nullable=True)
    estado = Column(String(2), nullable=True)
    comarca = Column(String(120), nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    matriculas = relationship(
        "Matricula",
        back_populates="cartorio",
        lazy="selectin",
    )
