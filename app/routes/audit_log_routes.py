from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.audit_log import AuditLogResponse
from app.crud.audit_log_crud import list_audit_logs

router = APIRouter()


@router.get(
    "/audit-logs/",
    response_model=list[AuditLogResponse],
)
def listar_audit_logs(
    entity_type: str | None = Query(default=None),
    entity_id: str | None = Query(default=None),
    action: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return list_audit_logs(
        db=db,
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        limit=limit,
    )
