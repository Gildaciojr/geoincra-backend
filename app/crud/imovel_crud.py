# app/crud/imovel_crud.py

from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.imovel import Imovel
from app.models.project import Project
from app.models.municipio import Municipio
from app.schemas.imovel import ImovelCreate, ImovelUpdate


# =====================================================
# Criar imóvel
# =====================================================
def create_imovel(db: Session, data: ImovelCreate):
    project = db.query(Project).filter(Project.id == data.project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Projeto não encontrado.")

    municipio = db.query(Municipio).filter(Municipio.id == data.municipio_id).first()
    if not municipio:
        raise HTTPException(status_code=404, detail="Município não encontrado.")

    imovel = Imovel(
        project_id=data.project_id,
        municipio_id=data.municipio_id,
        nome=data.nome,
        descricao=data.descricao,
        area_hectares=data.area_hectares,
        ccir=data.ccir,
        matricula_principal=data.matricula_principal,
    )

    db.add(imovel)
    db.commit()
    db.refresh(imovel)
    return imovel


# =====================================================
# Listar imóveis por projeto
# =====================================================
def list_imoveis_by_project(db: Session, project_id: int):
    return (
        db.query(Imovel)
        .filter(Imovel.project_id == project_id)
        .order_by(Imovel.id.asc())
        .all()
    )


# =====================================================
# Buscar imóvel por ID
# =====================================================
def get_imovel(db: Session, imovel_id: int):
    return db.query(Imovel).filter(Imovel.id == imovel_id).first()


# =====================================================
# Atualizar imóvel
# =====================================================
def update_imovel(db: Session, imovel_id: int, data: ImovelUpdate):
    imovel = get_imovel(db, imovel_id)
    if not imovel:
        return None

    payload = data.model_dump(exclude_unset=True)

    if "municipio_id" in payload:
        municipio = db.query(Municipio).filter(Municipio.id == payload["municipio_id"]).first()
        if not municipio:
            raise HTTPException(status_code=404, detail="Município não encontrado.")

    for field, value in payload.items():
        setattr(imovel, field, value)

    db.commit()
    db.refresh(imovel)
    return imovel


# =====================================================
# Deletar imóvel
# =====================================================
def delete_imovel(db: Session, imovel_id: int):
    imovel = get_imovel(db, imovel_id)
    if not imovel:
        return False

    db.delete(imovel)
    db.commit()
    return True
