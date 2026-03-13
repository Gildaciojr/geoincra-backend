from datetime import datetime
from sqlalchemy.orm import Session

from app.models.requerimento_campo import RequerimentoCampo


# =========================================================
# LISTAR POR PROJETO
# =========================================================

def list_by_project(db: Session, project_id: int):

    return (
        db.query(RequerimentoCampo)
        .filter(RequerimentoCampo.project_id == project_id)
        .order_by(RequerimentoCampo.updated_at.desc())
        .all()
    )


# =========================================================
# GET POR PROJETO + TIPO
# =========================================================

def get_by_project_and_tipo(
    db: Session,
    project_id: int,
    tipo: str,
):

    return (
        db.query(RequerimentoCampo)
        .filter(
            RequerimentoCampo.project_id == project_id,
            RequerimentoCampo.tipo == tipo,
        )
        .first()
    )


# =========================================================
# UPSERT POR PROJETO
# =========================================================

def upsert(
    db: Session,
    *,
    user_id: int,
    project_id: int,
    tipo: str,
    dados_json: dict,
    template_id: int | None,
    status: str | None,
):

    obj = get_by_project_and_tipo(
        db,
        project_id,
        tipo,
    )

    now = datetime.utcnow()

    if obj:

        obj.dados_json = dados_json or {}
        obj.template_id = template_id
        obj.status = status or obj.status
        obj.updated_at = now

        db.commit()
        db.refresh(obj)

        return obj

    obj = RequerimentoCampo(

        user_id=user_id,
        project_id=project_id,
        tipo=tipo,

        template_id=template_id,
        status=status or "RASCUNHO",

        dados_json=dados_json or {},

        created_at=now,
        updated_at=now,
    )

    db.add(obj)

    db.commit()
    db.refresh(obj)

    return obj


# =========================================================
# DELETE POR PROJETO
# =========================================================

def delete(
    db: Session,
    project_id: int,
    tipo: str,
):

    obj = get_by_project_and_tipo(
        db,
        project_id,
        tipo,
    )

    if not obj:
        return False

    db.delete(obj)
    db.commit()

    return True