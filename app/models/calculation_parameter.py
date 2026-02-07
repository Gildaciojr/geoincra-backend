from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean
from app.core.database import Base


class CalculationParameter(Base):
    __tablename__ = "calculation_parameters"

    id = Column(Integer, primary_key=True, index=True)

    # Nome lógico do parâmetro
    nome = Column("name", String(255), nullable=False, unique=True)

    descricao = Column(String(500), nullable=True)

    # Valor base
    valor = Column(Float, nullable=False)

    unidade = Column(String(50), nullable=True)      # ha, %, m, R$
    categoria = Column(String(100), nullable=True)   # geo, cartorio, art, imposto

    # Controle
    ativo = Column(Boolean, default=True, nullable=False)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
