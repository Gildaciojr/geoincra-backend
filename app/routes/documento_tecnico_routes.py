from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.imovel import Imovel

from app.schemas.documento_tecnico import (
    DocumentoTecnicoCreate,
    DocumentoTecnicoUpdate,
    DocumentoTecnicoResponse,
    DocumentoTecnicoNovaVersaoRequest,
)
from app.crud.documento_tecnico_crud import (
    create_documento_tecnico,
    list_documentos_tecnicos_by_imovel,
    list_documentos_tecnicos_atuais_by_imovel,
    get_documento_tecnico,
    update_documento_tecnico,
    criar_nova_versao,
    delete_documento_tecnico,
)
from app.services.documento_tecnico_guard_service import DocumentoTecnicoGuardService
from app.services.audit_service import AuditService

router = APIRouter()


# =========================================================
# HELPERS DE SEGURANÇA
# =========================================================
def _check_imovel_owner(db: Session, imovel_id: int, user_id: int):
    imovel = (
        db.query(Imovel)
        .join(Project)
        .filter(
            Imovel.id == imovel_id,
            Project.owner_id == user_id,
        )
        .first()
    )
    if not imovel:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")
    return imovel


def _check_documento_owner(db: Session, documento_id: int, user_id: int):
    documento = get_documento_tecnico(db, documento_id)
    if not documento:
        raise HTTPException(status_code=404, detail="Documento técnico não encontrado.")

    _check_imovel_owner(db, documento.imovel_id, user_id)
    return documento


# =========================================================
# CREATE
# =========================================================
@router.post(
    "/imoveis/{imovel_id}/documentos-tecnicos/",
    response_model=DocumentoTecnicoResponse,
)
def create_documento_tecnico_route(
    imovel_id: int,
    payload: DocumentoTecnicoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_imovel_owner(db, imovel_id, current_user.id)

    obj = create_documento_tecnico(db, imovel_id, payload)

    AuditService.log(
        db,
        entity_type="DocumentoTecnico",
        entity_id=str(obj.id),
        action="CREATE",
        source="api",
        payload_json={
            "imovel_id": obj.imovel_id,
            "document_group_key": obj.document_group_key,
            "versao": obj.versao,
            "status_tecnico": obj.status_tecnico,
        },
    )
    return obj


# =========================================================
# LIST
# =========================================================
@router.get(
    "/imoveis/{imovel_id}/documentos-tecnicos/",
    response_model=list[DocumentoTecnicoResponse],
)
def list_documentos_tecnicos_route(
    imovel_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_imovel_owner(db, imovel_id, current_user.id)
    return list_documentos_tecnicos_by_imovel(db, imovel_id)


@router.get(
    "/imoveis/{imovel_id}/documentos-tecnicos/atuais",
    response_model=list[DocumentoTecnicoResponse],
)
def list_documentos_tecnicos_atuais_route(
    imovel_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_imovel_owner(db, imovel_id, current_user.id)
    return list_documentos_tecnicos_atuais_by_imovel(db, imovel_id)


# =========================================================
# GET
# =========================================================
@router.get(
    "/documentos-tecnicos/{documento_id}",
    response_model=DocumentoTecnicoResponse,
)
def get_documento_tecnico_route(
    documento_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return _check_documento_owner(db, documento_id, current_user.id)


# =========================================================
# UPDATE
# =========================================================
@router.put(
    "/documentos-tecnicos/{documento_id}",
    response_model=DocumentoTecnicoResponse,
)
def update_documento_tecnico_route(
    documento_id: int,
    payload: DocumentoTecnicoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    atual = _check_documento_owner(db, documento_id, current_user.id)

    DocumentoTecnicoGuardService.bloquear_update_se_aprovado(atual)

    obj = update_documento_tecnico(db, documento_id, payload)

    AuditService.log(
        db,
        entity_type="DocumentoTecnico",
        entity_id=str(obj.id),
        action="UPDATE",
        source="api",
        payload_json={
            "status_tecnico": obj.status_tecnico,
            "is_versao_atual": obj.is_versao_atual,
        },
    )
    return obj


# =========================================================
# NOVA VERSÃO
# =========================================================
@router.post(
    "/documentos-tecnicos/{documento_id}/nova-versao",
    response_model=DocumentoTecnicoResponse,
)
def criar_nova_versao_route(
    documento_id: int,
    payload: DocumentoTecnicoNovaVersaoRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_documento_owner(db, documento_id, current_user.id)

    obj = criar_nova_versao(db, documento_id, payload)

    AuditService.log(
        db,
        entity_type="DocumentoTecnico",
        entity_id=str(obj.id),
        action="VERSION_CREATE",
        source="api",
        payload_json={
            "documento_origem_id": documento_id,
            "document_group_key": obj.document_group_key,
            "versao": obj.versao,
            "status_tecnico": obj.status_tecnico,
        },
    )
    return obj


# =========================================================
# DELETE
# =========================================================
@router.delete("/documentos-tecnicos/{documento_id}")
def delete_documento_tecnico_route(
    documento_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _check_documento_owner(db, documento_id, current_user.id)

    delete_documento_tecnico(db, documento_id)

    AuditService.log(
        db,
        entity_type="DocumentoTecnico",
        entity_id=str(documento_id),
        action="DELETE",
        source="api",
        payload_json={},
    )
    return {"deleted": True}
