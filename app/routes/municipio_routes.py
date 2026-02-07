# app/routes/municipio_routes.py

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.municipio import Municipio
from app.schemas.municipio import (
    MunicipioCreate,
    MunicipioUpdate,
    MunicipioResponse,
)

router = APIRouter(tags=["Municípios"])


# ============================================
# LISTAR MUNICÍPIOS
# GET /municipios?search=Ji&uf=RO
# ============================================
@router.get("/municipios", response_model=List[MunicipioResponse])
def list_municipios(
    search: Optional[str] = None,
    uf: Optional[str] = None,
    db: Session = Depends(get_db),
):
    query = db.query(Municipio)

    if search:
        query = query.filter(Municipio.nome.ilike(f"%{search}%"))

    if uf:
        query = query.filter(Municipio.estado == uf.upper())

    return query.order_by(Municipio.nome.asc()).all()


# ============================================
# GET POR ID
# ============================================
@router.get("/municipios/{municipio_id}", response_model=MunicipioResponse)
def get_municipio(municipio_id: int, db: Session = Depends(get_db)):
    municipio = db.query(Municipio).filter(Municipio.id == municipio_id).first()
    if not municipio:
        raise HTTPException(status_code=404, detail="Município não encontrado.")
    return municipio


# ============================================
# CREATE
# ============================================
@router.post("/municipios", response_model=MunicipioResponse)
def create_municipio(payload: MunicipioCreate, db: Session = Depends(get_db)):
    exists = (
        db.query(Municipio)
        .filter(Municipio.nome == payload.nome, Municipio.estado == payload.estado)
        .first()
    )
    if exists:
        raise HTTPException(status_code=400, detail="Município já cadastrado.")

    municipio = Municipio(**payload.model_dump())
    db.add(municipio)
    db.commit()
    db.refresh(municipio)
    return municipio


# ============================================
# UPDATE
# ============================================
@router.put("/municipios/{municipio_id}", response_model=MunicipioResponse)
def update_municipio(
    municipio_id: int,
    payload: MunicipioUpdate,
    db: Session = Depends(get_db),
):
    municipio = db.query(Municipio).filter(Municipio.id == municipio_id).first()
    if not municipio:
        raise HTTPException(status_code=404, detail="Município não encontrado.")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(municipio, field, value)

    db.commit()
    db.refresh(municipio)
    return municipio


# ============================================
# DELETE
# ============================================
@router.delete("/municipios/{municipio_id}")
def delete_municipio(municipio_id: int, db: Session = Depends(get_db)):
    municipio = db.query(Municipio).filter(Municipio.id == municipio_id).first()
    if not municipio:
        raise HTTPException(status_code=404, detail="Município não encontrado.")

    db.delete(municipio)
    db.commit()
    return {"detail": "Município removido com sucesso."}
