# app/models/requerimento_campo.py
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.core.database import Base


class RequerimentoCampo(Base):
    __tablename__ = "requerimento_campos"

    id = Column(Integer, primary_key=True, index=True)

    # =====================================================
    # 🔑 DONO DO REQUERIMENTO (OBRIGATÓRIO)
    # =====================================================
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # =====================================================
    # 🔗 PROJETO (OPCIONAL)
    # =====================================================
    project_id = Column(
        Integer,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # =====================================================
    # IDENTIDADE DO REQUERIMENTO
    # =====================================================
    tipo = Column(String(80), nullable=False)  # ex: "AVERBACAO", "USUCAPIAO", "CHECKLIST"
    template_id = Column(Integer, ForeignKey("templates.id"), nullable=True)

    # =====================================================
    # CONTEÚDO DINÂMICO
    # =====================================================
    dados_json = Column(JSONB, nullable=False, default=dict)

    # RASCUNHO | FINAL
    status = Column(String(30), nullable=False, default="RASCUNHO")

    created_at = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=False), default=datetime.utcnow, nullable=False)

    # =====================================================
    # RELACIONAMENTOS
    # =====================================================
    user = relationship("User", lazy="joined")
    project = relationship("Project", lazy="select")

    def __repr__(self) -> str:
        return (
            f"<RequerimentoCampo id={self.id} "
            f"user_id={self.user_id} "
            f"project_id={self.project_id} "
            f"tipo={self.tipo}>"
        )