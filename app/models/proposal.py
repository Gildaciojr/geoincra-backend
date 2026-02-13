from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base


class Proposal(Base):
    __tablename__ = "proposals"

    id = Column(Integer, primary_key=True, index=True)

    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
    )

    area = Column(Float, nullable=False)
    valor_base = Column(Float, nullable=False)
    valor_art = Column(Float, nullable=False)
    extras = Column(Float, nullable=False)
    total = Column(Float, nullable=False)

    # =========================
    # STATUS / ACEITE
    # =========================
    status = Column(
        String(20),
        nullable=False,
        default="GERADA",  # GERADA | ACEITA | CANCELADA
    )

    accepted_at = Column(DateTime(timezone=True), nullable=True)

    accepted_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # =========================
    # ARQUIVOS
    # =========================
    pdf_path = Column(String(500), nullable=True)
    contract_pdf_path = Column(String(500), nullable=True)

    html_proposta = Column(Text, nullable=True)
    html_contrato = Column(Text, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    project = relationship(
        "Project",
        back_populates="proposals",
        lazy="select",
    )
