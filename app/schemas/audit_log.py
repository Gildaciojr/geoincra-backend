from __future__ import annotations

from datetime import datetime
from typing import Optional, Dict

from pydantic import BaseModel, Field


class AuditLogBase(BaseModel):
    entity_type: str = Field(..., min_length=2, max_length=80)
    entity_id: str = Field(..., min_length=1, max_length=80)
    action: str = Field(..., min_length=2, max_length=40)

    actor_user_id: Optional[int] = None
    source: str = Field(default="api", min_length=2, max_length=30)

    payload_json: Optional[Dict[str, object]] = None


class AuditLogCreate(AuditLogBase):
    pass


class AuditLogResponse(AuditLogBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True
