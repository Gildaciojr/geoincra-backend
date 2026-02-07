from datetime import datetime
from sqlalchemy.orm import Session

from app.models.project_marco import ProjectMarco


def criar_marco(
    db: Session,
    project_id: int,
    codigo: str,
    titulo: str,
    descricao: str | None = None,
    automatico: bool = True,
) -> ProjectMarco:
    marco = ProjectMarco(
        project_id=project_id,
        codigo=codigo,
        titulo=titulo,
        descricao=descricao,
        criado_automaticamente=automatico,
    )
    db.add(marco)
    db.commit()
    db.refresh(marco)
    return marco


def marcar_como_atingido(
    db: Session,
    marco: ProjectMarco,
) -> ProjectMarco:
    marco.atingido = True
    marco.atingido_em = datetime.utcnow()
    db.commit()
    db.refresh(marco)
    return marco


def obter_marco(
    db: Session,
    project_id: int,
    codigo: str,
) -> ProjectMarco | None:
    return (
        db.query(ProjectMarco)
        .filter(
            ProjectMarco.project_id == project_id,
            ProjectMarco.codigo == codigo,
        )
        .first()
    )


def listar_marcos_projeto(
    db: Session,
    project_id: int,
) -> list[ProjectMarco]:
    return (
        db.query(ProjectMarco)
        .filter(ProjectMarco.project_id == project_id)
        .order_by(ProjectMarco.created_at.asc())
        .all()
    )
