from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.imovel import Imovel
from app.models.documento_tecnico import DocumentoTecnico

from app.schemas.documento_tecnico_checklist import (
    DocumentoTecnicoChecklistCreate,
    DocumentoTecnicoChecklistUpdate,
    DocumentoTecnicoChecklistResponse,
)
from app.crud.documento_tecnico_checklist_crud import (
    criar_item_checklist,
    listar_checklist_por_documento,
    atualizar_item_checklist,
    deletar_item_checklist,
)
from app.services.documento_tecnico_orquestracao_service import (
    DocumentoTecnicoOrquestracaoService,
)

router = APIRouter()


# =========================================================
# HELPERS DE SEGURANÇA
# =========================================================
def _check_documento_owner(db: Session, documento_id: int, user_id: int):
    documento = (
        db.query(DocumentoTecnico)
        .join(Imovel)
        .join(Project)
        .filter(
            DocumentoTecnico.id == documento_id,
            Project.owner_id == user_id,
        )
        .first()
    )
    if not documento:
        raise HTTPException(status_code=404, detail="Documento técnico não encontrado")
    return documento


# =========================================================
# CREATE
# =========================================================
@router.post(
    "/documentos-tecnicos/{documento_tecnico_id}/checklist/",
    response_model=DocumentoTecnicoChecklistResponse,
)
def create_checklist_item(
    documento_tecnico_id: int,
    payload: DocumentoTecnicoChecklistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    documento = _check_documento_owner(db, documento_tecnico_id, current_user.id)

    item = criar_item_checklist(db, documento_tecnico_id, payload)

    DocumentoTecnicoOrquestracaoService.processar_evento_documento_tecnico(
        db=db,
        documento=documento,
    )
    return item


# =========================================================
# LIST
# =========================================================
@router.get(
    "/documentos-tecnicos/{documento_tecnico_id}/checklist/",
    response_model=list[DocumentoTecnicoChecklistResponse],
)
def list_checklist_items(
    documento_tecnico_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_documento_owner(db, documento_tecnico_id, current_user.id)
    return listar_checklist_por_documento(db, documento_tecnico_id)


# =========================================================
# UPDATE
# =========================================================
@router.put(
    "/documentos-tecnicos/checklist/{checklist_id}",
    response_model=DocumentoTecnicoChecklistResponse,
)
def update_checklist_item(
    checklist_id: int,
    payload: DocumentoTecnicoChecklistUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = atualizar_item_checklist(db, checklist_id, payload)
    if not item:
        raise HTTPException(status_code=404, detail="Item de checklist não encontrado.")

    documento = _check_documento_owner(
        db,
        item.documento_tecnico_id,
        current_user.id,
    )

    DocumentoTecnicoOrquestracaoService.processar_evento_documento_tecnico(
        db=db,
        documento=documento,
    )
    return item


# =========================================================
# DELETE
# =========================================================
@router.delete("/documentos-tecnicos/checklist/{checklist_id}")
def delete_checklist_item(
    checklist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    item = deletar_item_checklist(db, checklist_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item de checklist não encontrado.")

    _check_documento_owner(db, item.documento_tecnico_id, current_user.id)
    return {"deleted": True}
