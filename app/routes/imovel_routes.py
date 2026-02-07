from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user_required
from app.schemas.imovel import (
    ImovelCreate,
    ImovelUpdate,
    ImovelResponse,
)
from app.crud.imovel_crud import (
    create_imovel,
    list_imoveis_by_project,
    get_imovel,
    update_imovel,
    delete_imovel,
)

router = APIRouter()


# ============================================
# 🔒 Criar imóvel (login obrigatório)
# ============================================
@router.post("/imoveis", response_model=ImovelResponse)
def create_imovel_route(
    payload: ImovelCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_required),
):
    return create_imovel(db, payload)


# ============================================
# 🔓 Listar imóveis por projeto (visitante ok)
# ============================================
@router.get("/projects/{project_id}/imoveis", response_model=list[ImovelResponse])
def list_imoveis_route(project_id: int, db: Session = Depends(get_db)):
    return list_imoveis_by_project(db, project_id)


# ============================================
# 🔓 Buscar imóvel (visitante ok)
# ============================================
@router.get("/imoveis/{imovel_id}", response_model=ImovelResponse)
def get_imovel_route(imovel_id: int, db: Session = Depends(get_db)):
    imovel = get_imovel(db, imovel_id)
    if not imovel:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado.")
    return imovel


# ============================================
# 🔒 Atualizar imóvel
# ============================================
@router.put("/imoveis/{imovel_id}", response_model=ImovelResponse)
def update_imovel_route(
    imovel_id: int,
    payload: ImovelUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_required),
):
    imovel = update_imovel(db, imovel_id, payload)
    if not imovel:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado.")
    return imovel


# ============================================
# 🔒 Deletar imóvel
# ============================================
@router.delete("/imoveis/{imovel_id}")
def delete_imovel_route(
    imovel_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_required),
):
    success = delete_imovel(db, imovel_id)
    if not success:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado.")
    return {"status": "ok", "deleted_id": imovel_id}
