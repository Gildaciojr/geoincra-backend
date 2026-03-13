from sqlalchemy.orm import Session

from app.models.visita_tecnica import VisitaTecnica
from app.models.project import Project
from app.models.profissional import Profissional

from app.schemas.visita_tecnica import (
    VisitaTecnicaCreate,
    VisitaTecnicaUpdate,
)


def criar_visita(
    db: Session,
    project_id: int,
    data: VisitaTecnicaCreate,
) -> VisitaTecnica:

    project = db.query(Project).get(project_id)
    if not project:
        raise ValueError("Projeto não encontrado.")

    profissional = db.query(Profissional).get(data.profissional_id)
    if not profissional:
        raise ValueError("Profissional não encontrado.")

    visita = VisitaTecnica(
        project_id=project_id,
        profissional_id=data.profissional_id,
        data_agendada=data.data_agendada,
        observacoes=data.observacoes,
    )

    db.add(visita)
    db.commit()
    db.refresh(visita)

    return visita


def listar_visitas_projeto(
    db: Session,
    project_id: int,
):
    return (
        db.query(VisitaTecnica)
        .filter(VisitaTecnica.project_id == project_id)
        .order_by(VisitaTecnica.data_agendada.asc())
        .all()
    )


def agenda_profissional(
    db: Session,
    profissional_id: int,
):
    return (
        db.query(VisitaTecnica)
        .filter(VisitaTecnica.profissional_id == profissional_id)
        .order_by(VisitaTecnica.data_agendada.asc())
        .all()
    )


def atualizar_visita(
    db: Session,
    visita_id: int,
    data: VisitaTecnicaUpdate,
):

    visita = db.query(VisitaTecnica).get(visita_id)

    if not visita:
        return None

    payload = data.model_dump(exclude_unset=True)

    for field, value in payload.items():
        setattr(visita, field, value)

    db.commit()
    db.refresh(visita)

    return visita