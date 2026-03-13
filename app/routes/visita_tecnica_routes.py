from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db

from app.schemas.visita_tecnica import (
    VisitaTecnicaCreate,
    VisitaTecnicaUpdate,
    VisitaTecnicaResponse,
)

from app.crud.visita_tecnica_crud import (
    criar_visita,
    listar_visitas_projeto,
    agenda_profissional,
    atualizar_visita,
)

router = APIRouter()


@router.post(
    "/projects/{project_id}/visitas",
    response_model=VisitaTecnicaResponse,
)
def criar_visita_route(
    project_id: int,
    payload: VisitaTecnicaCreate,
    db: Session = Depends(get_db),
):
    try:
        return criar_visita(db, project_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get(
    "/projects/{project_id}/visitas",
    response_model=list[VisitaTecnicaResponse],
)
def listar_visitas_route(
    project_id: int,
    db: Session = Depends(get_db),
):
    return listar_visitas_projeto(db, project_id)


@router.get(
    "/profissionais/{profissional_id}/agenda",
    response_model=list[VisitaTecnicaResponse],
)
def agenda_profissional_route(
    profissional_id: int,
    db: Session = Depends(get_db),
):
    return agenda_profissional(db, profissional_id)


@router.patch(
    "/visitas/{visita_id}",
    response_model=VisitaTecnicaResponse,
)
def atualizar_visita_route(
    visita_id: int,
    payload: VisitaTecnicaUpdate,
    db: Session = Depends(get_db),
):
    visita = atualizar_visita(db, visita_id, payload)

    if not visita:
        raise HTTPException(status_code=404, detail="Visita não encontrada.")

    return visita