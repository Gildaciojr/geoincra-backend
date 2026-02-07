from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogCreate


def create_audit_log(db: Session, data: AuditLogCreate) -> AuditLog:
    obj = AuditLog(
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        action=data.action,
        actor_user_id=data.actor_user_id,
        source=data.source,
        payload_json=data.payload_json,
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_audit_logs(
    db: Session,
    entity_type: str | None = None,
    entity_id: str | None = None,
    action: str | None = None,
    limit: int = 100,
) -> list[AuditLog]:
    q = db.query(AuditLog)

    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if entity_id:
        q = q.filter(AuditLog.entity_id == entity_id)
    if action:
        q = q.filter(AuditLog.action == action)

    return q.order_by(AuditLog.created_at.desc()).limit(limit).all()
