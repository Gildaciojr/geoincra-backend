from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.core.database import Base


class SigefExport(Base):
    __tablename__ = "sigef_exports"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    imovel_id = Column(
        Integer,
        ForeignKey("imoveis.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status = Column(
        String(30),
        nullable=False,
        default="PENDING",  # PENDING | READY | ERROR | SUBMITTED
    )

    payload_json = Column(Text, nullable=True)
    arquivo_gerado = Column(String(255), nullable=True)

    erro = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    project = relationship("Project", lazy="joined")
    imovel = relationship("Imovel", lazy="joined")
