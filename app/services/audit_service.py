from __future__ import annotations

from sqlalchemy.orm import Session

from app.crud.audit_log_crud import create_audit_log
from app.schemas.audit_log import AuditLogCreate


class AuditService:
    """
    Serviço central para registrar eventos relevantes do CORE.
    Não depende de APIs externas.
    """

    @staticmethod
    def log(
        db: Session,
        *,
        entity_type: str,
        entity_id: str,
        action: str,
        source: str = "api",
        actor_user_id: int | None = None,
        payload_json: dict[str, object] | None = None,
    ):
        data = AuditLogCreate(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            actor_user_id=actor_user_id,
            source=source,
            payload_json=payload_json,
        )
        return create_audit_log(db, data)
