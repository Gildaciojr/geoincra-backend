from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user_required
from app.models.user import User
from app.schemas.requerimento import RequerimentoUpsert, RequerimentoOut
from app.crud.requerimento_crud import (
    list_by_user,
    upsert,
    attach_to_project,
    delete,
)

router = APIRouter(
    prefix="/requerimentos",
    tags=["Requerimentos (Usuário)"],
)


# =====================================================
# LISTAR TODOS OS REQUERIMENTOS DO USUÁRIO
# =====================================================
@router.get("", response_model=list[RequerimentoOut])
def list_my_requerimentos(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    return list_by_user(db, current_user.id)


# =====================================================
# CRIAR / ATUALIZAR REQUERIMENTO LIVRE
# =====================================================
@router.post("", response_model=RequerimentoOut)
def upsert_requerimento(
    payload: RequerimentoUpsert,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    return upsert(
        db=db,
        user_id=current_user.id,
        project_id=None,
        tipo=payload.tipo,
        template_id=payload.template_id,
        status=payload.status,
        dados_json=payload.dados_json,
    )


# =====================================================
# VINCULAR REQUERIMENTO A UM PROJETO
# =====================================================
@router.post("/{requerimento_id}/attach/{project_id}", response_model=RequerimentoOut)
def attach_requerimento_to_project(
    requerimento_id: int,
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    obj = attach_to_project(
        db=db,
        requerimento_id=requerimento_id,
        project_id=project_id,
    )

    if not obj or obj.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Requerimento não encontrado")

    return obj


# =====================================================
# DELETE
# =====================================================
@router.delete("/{requerimento_id}")
def delete_requerimento(
    requerimento_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    ok = delete(
        db=db,
        user_id=current_user.id,
        requerimento_id=requerimento_id,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="Requerimento não encontrado")

    return {"deleted": True}