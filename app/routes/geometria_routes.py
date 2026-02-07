from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.geometria import GeometriaCreate, GeometriaUpdate, GeometriaResponse
from app.crud.geometria_crud import (
    create_geometria,
    list_geometrias,
    get_geometria,
    update_geometria,
    delete_geometria,
)

router = APIRouter()


@router.post("/imoveis/{imovel_id}/geometrias/", response_model=GeometriaResponse)
def create_geometria_route(imovel_id: int, payload: GeometriaCreate, db: Session = Depends(get_db)):
    return create_geometria(db, imovel_id, payload)


@router.get("/imoveis/{imovel_id}/geometrias/", response_model=list[GeometriaResponse])
def list_geometrias_route(imovel_id: int, db: Session = Depends(get_db)):
    return list_geometrias(db, imovel_id)


@router.get("/geometrias/{geometria_id}", response_model=GeometriaResponse)
def get_geometria_route(geometria_id: int, db: Session = Depends(get_db)):
    obj = get_geometria(db, geometria_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Geometria não encontrada.")
    return obj


@router.put("/geometrias/{geometria_id}", response_model=GeometriaResponse)
def update_geometria_route(geometria_id: int, payload: GeometriaUpdate, db: Session = Depends(get_db)):
    obj = update_geometria(db, geometria_id, payload)
    if not obj:
        raise HTTPException(status_code=404, detail="Geometria não encontrada.")
    return obj


@router.delete("/geometrias/{geometria_id}")
def delete_geometria_route(geometria_id: int, db: Session = Depends(get_db)):
    ok = delete_geometria(db, geometria_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Geometria não encontrada.")
    return {"deleted": True}
