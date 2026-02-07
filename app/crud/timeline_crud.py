from sqlalchemy.orm import Session
from app.models.timeline import TimelineEntry
from app.schemas.timeline import TimelineCreate


def create_timeline_entry(db: Session, project_id: int, data: TimelineCreate):
    entry = TimelineEntry(
        project_id=project_id,
        created_by_user_id=data.created_by_user_id,
        titulo=data.titulo,
        descricao=data.descricao,
        status=data.status,
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def list_timeline_for_project(db: Session, project_id: int):
    return (
        db.query(TimelineEntry)
        .filter(TimelineEntry.project_id == project_id)
        .order_by(TimelineEntry.created_at.desc())
        .all()
    )


def get_entry_by_id(db: Session, entry_id: int):
    return db.query(TimelineEntry).filter(TimelineEntry.id == entry_id).first()


def delete_entry(db: Session, entry_id: int):
    entry = get_entry_by_id(db, entry_id)
    if not entry:
        return False

    db.delete(entry)
    db.commit()
    return True
