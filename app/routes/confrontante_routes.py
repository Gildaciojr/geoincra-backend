from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.imovel import Imovel
from app.schemas.confrontante import (
    ConfrontanteCreate,
    ConfrontanteUpdate,
    ConfrontanteResponse,
)
from app.crud.confrontante_crud import (
    create_confrontante,
    list_confrontantes,
    get_confrontante,
    update_confrontante,
    delete_confrontante,
)

router = APIRouter(tags=["Confrontantes"])


# ============================================================
# ✅ PADRÃO CORRETO: CONFRONTANTES POR IMÓVEL
# ============================================================

@router.post("/imoveis/{imovel_id}/confrontantes", response_model=ConfrontanteResponse)
def create_confrontante_by_imovel(
    imovel_id: int,
    body: ConfrontanteCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_confrontante(db, imovel_id, body)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/imoveis/{imovel_id}/confrontantes", response_model=list[ConfrontanteResponse])
def list_confrontantes_by_imovel(
    imovel_id: int,
    db: Session = Depends(get_db),
):
    return list_confrontantes(db, imovel_id)


# ============================================================
# ✅ COMPATIBILIDADE: ROTAS LEGADAS POR PROJETO
# ============================================================

@router.post("/projects/{project_id}/confrontantes", response_model=ConfrontanteResponse)
def create_confrontante_legacy_project(
    project_id: int,
    body: ConfrontanteCreate,
    db: Session = Depends(get_db),
):
    imovel = (
        db.query(Imovel)
        .filter(Imovel.project_id == project_id)
        .order_by(Imovel.id.asc())
        .first()
    )
    if not imovel:
        raise HTTPException(
            status_code=404,
            detail="Projeto não possui imóvel cadastrado. Crie um imóvel antes.",
        )

    try:
        return create_confrontante(db, imovel.id, body)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/projects/{project_id}/confrontantes", response_model=list[ConfrontanteResponse])
def list_confrontantes_legacy_project(
    project_id: int,
    db: Session = Depends(get_db),
):
    imoveis = db.query(Imovel).filter(Imovel.project_id == project_id).all()
    if not imoveis:
        return []

    result: list[ConfrontanteResponse] = []
    for imovel in imoveis:
        result.extend(list_confrontantes(db, imovel.id))
    return result


# ============================================================
# CRUD DIRETO POR ID
# ============================================================

@router.get("/confrontantes/{confrontante_id}", response_model=ConfrontanteResponse)
def get_confrontante_route(
    confrontante_id: int,
    db: Session = Depends(get_db),
):
    item = get_confrontante(db, confrontante_id)
    if not item:
        raise HTTPException(status_code=404, detail="Confrontante não encontrado.")
    return item


@router.put("/confrontantes/{confrontante_id}", response_model=ConfrontanteResponse)
def update_confrontante_route(
    confrontante_id: int,
    body: ConfrontanteUpdate,
    db: Session = Depends(get_db),
):
    item = update_confrontante(db, confrontante_id, body)
    if not item:
        raise HTTPException(status_code=404, detail="Confrontante não encontrado.")
    return item


@router.delete("/confrontantes/{confrontante_id}")
def delete_confrontante_route(
    confrontante_id: int,
    db: Session = Depends(get_db),
):
    ok = delete_confrontante(db, confrontante_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Confrontante não encontrado.")
    return {"deleted": True, "id": confrontante_id}
