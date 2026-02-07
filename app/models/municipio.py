from sqlalchemy import Column, Integer, String, Float, Index
from app.core.database import Base


class Municipio(Base):
    __tablename__ = "municipios"

    id = Column(Integer, primary_key=True, index=True)

    nome = Column(String(120), nullable=False)
    estado = Column(String(2), nullable=False, index=True)

    vti_min = Column(Float, nullable=False)
    vtn_min = Column(Float, nullable=False)

    __table_args__ = (
        Index("ix_municipio_nome_estado", "nome", "estado", unique=True),
    )
