from datetime import datetime
from sqlalchemy.orm import Session

from app.models.timeline import TimelineEntry


class TimelineService:

    @staticmethod
    def registrar_evento(
        db: Session,
        project_id: int,
        titulo: str,
        descricao: str | None = None,
        status: str | None = None,
    ):
        entry = TimelineEntry(
            project_id=project_id,
            titulo=titulo,
            descricao=descricao,
            status=status,
            created_at=datetime.utcnow(),
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry
