from datetime import datetime
from sqlalchemy.orm import Session

from app.models.documento_tecnico import DocumentoTecnico
from app.models.documento_tecnico_checklist import DocumentoTecnicoChecklist
from app.schemas.documento_tecnico_checklist import (
    DocumentoTecnicoChecklistCreate,
    DocumentoTecnicoChecklistUpdate,
)


def criar_item_checklist(
    db: Session,
    documento_tecnico_id: int,
    data: DocumentoTecnicoChecklistCreate,
) -> DocumentoTecnicoChecklist:
    doc = db.query(DocumentoTecnico).get(documento_tecnico_id)
    if not doc:
        raise ValueError("Documento técnico não encontrado.")

    item = DocumentoTecnicoChecklist(
        documento_tecnico_id=documento_tecnico_id,
        chave=data.chave,
        descricao=data.descricao,
        obrigatorio=data.obrigatorio,
        status=data.status,
        mensagem=data.mensagem,
        validado_automaticamente=data.validado_automaticamente,
    )

    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def listar_checklist_por_documento(
    db: Session,
    documento_tecnico_id: int,
) -> list[DocumentoTecnicoChecklist]:
    return (
        db.query(DocumentoTecnicoChecklist)
        .filter(DocumentoTecnicoChecklist.documento_tecnico_id == documento_tecnico_id)
        .order_by(DocumentoTecnicoChecklist.id.asc())
        .all()
    )


def atualizar_item_checklist(
    db: Session,
    checklist_id: int,
    data: DocumentoTecnicoChecklistUpdate,
) -> DocumentoTecnicoChecklist | None:
    item = db.query(DocumentoTecnicoChecklist).get(checklist_id)
    if not item:
        return None

    payload = data.model_dump(exclude_unset=True)

    for field, value in payload.items():
        setattr(item, field, value)

    if "status" in payload:
        item.validado_em = datetime.utcnow()

    db.commit()
    db.refresh(item)
    return item


def deletar_item_checklist(
    db: Session,
    checklist_id: int,
) -> bool:
    item = db.query(DocumentoTecnicoChecklist).get(checklist_id)
    if not item:
        return False

    db.delete(item)
    db.commit()
    return True
