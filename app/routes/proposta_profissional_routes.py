from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.proposta_profissional import (
    PropostaProfissionalCreate,
    PropostaProfissionalResposta,
    PropostaProfissionalResponse,
)
from app.crud.proposta_profissional_crud import (
    enviar_proposta,
    responder_proposta,
    listar_propostas_por_projeto,
)

router = APIRouter()


# =========================================================
# ENVIAR PROPOSTA
# =========================================================
@router.post(
    "/projects/{project_id}/propostas/",
    response_model=PropostaProfissionalResponse,
)
def enviar_proposta_route(
    project_id: int,
    payload: PropostaProfissionalCreate,
    db: Session = Depends(get_db),
):
    try:
        return enviar_proposta(db, project_id, payload)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =========================================================
# RESPONDER PROPOSTA
# =========================================================
@router.post(
    "/propostas/{proposta_id}/responder",
    response_model=PropostaProfissionalResponse,
)
def responder_proposta_route(
    proposta_id: int,
    payload: PropostaProfissionalResposta,
    db: Session = Depends(get_db),
):
    try:
        proposta = responder_proposta(db, proposta_id, payload)
        if not proposta:
            raise HTTPException(status_code=404, detail="Proposta não encontrada.")
        return proposta
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# =========================================================
# LISTAR POR PROJETO
# =========================================================
@router.get(
    "/projects/{project_id}/propostas/",
    response_model=list[PropostaProfissionalResponse],
)
def listar_propostas_route(
    project_id: int,
    db: Session = Depends(get_db),
):
    return listar_propostas_por_projeto(db, project_id)
