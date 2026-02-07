from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    JSON,
    Index,
)
from app.core.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    __table_args__ = (
        Index("ix_audit_entity", "entity_type", "entity_id"),
        Index("ix_audit_action", "action"),
        Index("ix_audit_created_at", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)

    # Ex.: "Project", "Imovel", "DocumentoTecnico", "Pagamento", etc.
    entity_type = Column(String(80), nullable=False)

    # ID da entidade (mantemos string para suportar int/uuid futuramente)
    entity_id = Column(String(80), nullable=False)

    # Ex.: "CREATE", "UPDATE", "DELETE", "STATUS_CHANGE", "AUTO_EVENT"
    action = Column(String(40), nullable=False)

    # Usuário responsável (quando existir)
    actor_user_id = Column(Integer, nullable=True)

    # Origem do evento (ex.: "api", "system", "automation")
    source = Column(String(30), nullable=False, default="api")

    # Conteúdo estruturado: diffs, payload, metadados técnicos, etc.
    payload_json = Column(JSON, nullable=True)

    created_at = Column(
        DateTime(timezone=True),
        default=datetime.utcnow,
        nullable=False,
    )

    def __repr__(self) -> str:
        return (
            f"<AuditLog id={self.id} entity={self.entity_type}:{self.entity_id} "
            f"action={self.action} source={self.source}>"
        )
