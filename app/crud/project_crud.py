from sqlalchemy.orm import Session
from app.models.project import Project
from app.schemas.project import ProjectCreate, ProjectUpdate


def create_project(db: Session, payload: ProjectCreate, owner_id: int):
    project = Project(
        **payload.dict(),
        owner_id=owner_id,
    )
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def list_projects(db: Session, owner_id: int):
    return db.query(Project).filter(Project.owner_id == owner_id).all()


def get_project(db: Session, project_id: int):
    return db.query(Project).filter(Project.id == project_id).first()


def update_project(db: Session, project_id: int, payload: ProjectUpdate):
    project = get_project(db, project_id)
    if not project:
        return None

    for field, value in payload.dict(exclude_unset=True).items():
        setattr(project, field, value)

    db.commit()
    db.refresh(project)
    return project


def delete_project(db: Session, project_id: int):
    project = get_project(db, project_id)
    if not project:
        return False

    db.delete(project)
    db.commit()
    return True
