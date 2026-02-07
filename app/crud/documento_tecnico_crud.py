from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.imovel import Imovel
from app.models.documento_tecnico import DocumentoTecnico
from app.schemas.documento_tecnico import (
    DocumentoTecnicoCreate,
    DocumentoTecnicoUpdate,
    DocumentoTecnicoNovaVersaoRequest,
)


# =========================================================
# HELPERS
# =========================================================
def _validar_imovel(db: Session, imovel_id: int) -> Imovel:
    imovel = db.query(Imovel).filter(Imovel.id == imovel_id).first()
    if not imovel:
        raise ValueError("Imóvel não encontrado.")
    return imovel


def _get_versao_atual(
    db: Session,
    imovel_id: int,
    document_group_key: str,
) -> DocumentoTecnico | None:
    return (
        db.query(DocumentoTecnico)
        .filter(
            and_(
                DocumentoTecnico.imovel_id == imovel_id,
                DocumentoTecnico.document_group_key == document_group_key,
                DocumentoTecnico.is_versao_atual.is_(True),
            )
        )
        .first()
    )


def _get_max_versao(
    db: Session,
    imovel_id: int,
    document_group_key: str,
) -> int:
    row = (
        db.query(DocumentoTecnico.versao)
        .filter(
            and_(
                DocumentoTecnico.imovel_id == imovel_id,
                DocumentoTecnico.document_group_key == document_group_key,
            )
        )
        .order_by(DocumentoTecnico.versao.desc())
        .first()
    )
    return int(row[0]) if row else 0


# =========================================================
# CREATE
# =========================================================
def create_documento_tecnico(
    db: Session,
    imovel_id: int,
    data: DocumentoTecnicoCreate,
) -> DocumentoTecnico:
    _validar_imovel(db, imovel_id)

    versao = data.versao
    if versao is None:
        versao = _get_max_versao(db, imovel_id, data.document_group_key) + 1

    # Desativa versão atual anterior (se existir)
    anterior = _get_versao_atual(db, imovel_id, data.document_group_key)
    if anterior:
        anterior.is_versao_atual = False

    obj = DocumentoTecnico(
        imovel_id=imovel_id,
        document_group_key=data.document_group_key,
        versao=versao,
        is_versao_atual=True,
        tipo=data.tipo,
        status_tecnico=data.status_tecnico,
        observacoes_tecnicas=data.observacoes_tecnicas,
        conteudo_texto=data.conteudo_texto,
        conteudo_json=data.conteudo_json,
        arquivo_path=data.arquivo_path,
        metadata_json=data.metadata_json,
        gerado_em=data.gerado_em,
    )

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


# =========================================================
# LIST
# =========================================================
def list_documentos_tecnicos_by_imovel(
    db: Session,
    imovel_id: int,
) -> list[DocumentoTecnico]:
    _validar_imovel(db, imovel_id)

    return (
        db.query(DocumentoTecnico)
        .filter(DocumentoTecnico.imovel_id == imovel_id)
        .order_by(
            DocumentoTecnico.document_group_key.asc(),
            DocumentoTecnico.versao.desc(),
        )
        .all()
    )


def list_documentos_tecnicos_atuais_by_imovel(
    db: Session,
    imovel_id: int,
) -> list[DocumentoTecnico]:
    _validar_imovel(db, imovel_id)

    return (
        db.query(DocumentoTecnico)
        .filter(
            and_(
                DocumentoTecnico.imovel_id == imovel_id,
                DocumentoTecnico.is_versao_atual.is_(True),
            )
        )
        .order_by(DocumentoTecnico.document_group_key.asc())
        .all()
    )


# =========================================================
# GET
# =========================================================
def get_documento_tecnico(
    db: Session,
    documento_id: int,
) -> DocumentoTecnico | None:
    return (
        db.query(DocumentoTecnico)
        .filter(DocumentoTecnico.id == documento_id)
        .first()
    )


# =========================================================
# UPDATE
# =========================================================
def update_documento_tecnico(
    db: Session,
    documento_id: int,
    data: DocumentoTecnicoUpdate,
) -> DocumentoTecnico | None:
    obj = get_documento_tecnico(db, documento_id)
    if not obj:
        return None

    payload = data.model_dump(exclude_unset=True, exclude_none=True)
    for field, value in payload.items():
        setattr(obj, field, value)

    db.commit()
    db.refresh(obj)
    return obj


# =========================================================
# VERSIONAMENTO (NOVA VERSÃO)
# =========================================================
def criar_nova_versao(
    db: Session,
    documento_id: int,
    data: DocumentoTecnicoNovaVersaoRequest,
) -> DocumentoTecnico:
    anterior = get_documento_tecnico(db, documento_id)
    if not anterior:
        raise ValueError("Documento técnico não encontrado.")

    # Desativa a versão atual anterior
    anterior.is_versao_atual = False

    prox_versao = _get_max_versao(
        db,
        anterior.imovel_id,
        anterior.document_group_key,
    ) + 1

    obj = DocumentoTecnico(
        imovel_id=anterior.imovel_id,
        document_group_key=anterior.document_group_key,
        versao=prox_versao,
        is_versao_atual=True,
        tipo=data.tipo if data.tipo else anterior.tipo,
        status_tecnico=data.status_tecnico,
        observacoes_tecnicas=data.observacoes_tecnicas,
        conteudo_texto=data.conteudo_texto,
        conteudo_json=data.conteudo_json,
        arquivo_path=data.arquivo_path,
        metadata_json=data.metadata_json,
        gerado_em=data.gerado_em,
    )

    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


# =========================================================
# DELETE
# =========================================================
def delete_documento_tecnico(
    db: Session,
    documento_id: int,
) -> bool:
    obj = get_documento_tecnico(db, documento_id)
    if not obj:
        return False

    imovel_id = obj.imovel_id
    group_key = obj.document_group_key
    deleting_is_atual = bool(obj.is_versao_atual)

    db.delete(obj)
    db.commit()

    # Se deletou a versão atual, precisamos promover a última versão restante como atual
    if deleting_is_atual:
        novo_atual = (
            db.query(DocumentoTecnico)
            .filter(
                and_(
                    DocumentoTecnico.imovel_id == imovel_id,
                    DocumentoTecnico.document_group_key == group_key,
                )
            )
            .order_by(DocumentoTecnico.versao.desc())
            .first()
        )
        if novo_atual:
            novo_atual.is_versao_atual = True
            db.commit()

    return True
