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

    # =========================================================
    # ✅ STATUS INICIAL AUTOMÁTICO (REGRA DE DOMÍNIO)
    # Todo projeto nasce com estado válido e histórico
    # =========================================================
    from app.schemas.project_status import ProjectStatusCreate
    from app.crud.project_status_crud import definir_status_projeto

    definir_status_projeto(
        db=db,
        project_id=project.id,
        data=ProjectStatusCreate(
            status="CADASTRADO",
            descricao="Projeto criado no sistema.",
            definido_automaticamente=True,
            definido_por_usuario_id=None,
        ),
    )

    return project



def list_projects(db: Session, owner_id: int):
    return db.query(Project).filter(Project.owner_id == owner_id).all()

def list_projects_card(db: Session, owner_id: int):
    projects = (
        db.query(Project)
        .filter(Project.owner_id == owner_id)
        .all()
    )

    result = []
    for p in projects:
        result.append({
            "id": p.id,
            "name": p.name,
            "municipio": p.municipio,
            "uf": p.uf,
            "status": p.status,
            "created_at": p.created_at,
            "total_documents": len(p.documents),
            "total_proposals": len(p.proposals),
        })

    return result



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
