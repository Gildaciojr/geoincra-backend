from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user_required
from app.models.user import User
from app.models.project import Project
from app.crud.timeline_crud import (
    create_timeline_entry,
    list_timeline_for_project,
    get_entry_by_id,
    delete_entry,
)
from app.schemas.timeline import TimelineCreate, TimelineResponse

router = APIRouter(prefix="/projects", tags=["Projetos - Timeline"])


def _check_project_owner(db: Session, project_id: int, user_id: int) -> Project:
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.owner_id == user_id,
        )
        .first()
    )
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")
    return project


@router.post("/{project_id}/timeline", response_model=TimelineResponse)
def create_timeline_route(
    project_id: int,
    payload: TimelineCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    _check_project_owner(db, project_id, current_user.id)
    return create_timeline_entry(db, project_id, payload)


@router.get("/{project_id}/timeline", response_model=list[TimelineResponse])
def list_timeline_route(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    _check_project_owner(db, project_id, current_user.id)
    return list_timeline_for_project(db, project_id)


@router.get("/timeline/{entry_id}", response_model=TimelineResponse)
def get_entry_route(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    entry = get_entry_by_id(db, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Timeline entry not found")

    _check_project_owner(db, entry.project_id, current_user.id)
    return entry


@router.delete("/timeline/{entry_id}")
def delete_entry_route(
    entry_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    entry = get_entry_by_id(db, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Timeline entry not found")

    _check_project_owner(db, entry.project_id, current_user.id)
    delete_entry(db, entry_id)
    return {"status": "ok", "deleted_id": entry_id}
