# app/routes/cartorio_routes.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.cartorio import (
    CartorioCreate,
    CartorioUpdate,
    CartorioResponse,
)
from app.crud.cartorio_crud import (
    create_cartorio,
    list_cartorios,
    get_cartorio,
    update_cartorio,
    delete_cartorio,
)

router = APIRouter()


@router.get("/cartorios/", response_model=list[CartorioResponse])
def list_route(db: Session = Depends(get_db)):
    return list_cartorios(db)


@router.get("/cartorios/{cartorio_id}", response_model=CartorioResponse)
def get_route(cartorio_id: int, db: Session = Depends(get_db)):
    cartorio = get_cartorio(db, cartorio_id)
    if not cartorio:
        raise HTTPException(404, "Cartório não encontrado")
    return cartorio


@router.post("/cartorios/", response_model=CartorioResponse)
def create_route(data: CartorioCreate, db: Session = Depends(get_db)):
    return create_cartorio(db, data)


@router.put("/cartorios/{cartorio_id}", response_model=CartorioResponse)
def update_route(cartorio_id: int, data: CartorioUpdate, db: Session = Depends(get_db)):
    updated = update_cartorio(db, cartorio_id, data)
    if not updated:
        raise HTTPException(404, "Cartório não encontrado")
    return updated


@router.delete("/cartorios/{cartorio_id}")
def delete_route(cartorio_id: int, db: Session = Depends(get_db)):
    deleted = delete_cartorio(db, cartorio_id)
    if not deleted:
        raise HTTPException(404, "Cartório não encontrado")
    return {"status": "ok", "deleted": cartorio_id}
