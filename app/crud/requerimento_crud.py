# app/crud/requerimento_crud.py
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.requerimento_campo import RequerimentoCampo


# =====================================================
# GET ÚNICO (USER + TIPO + PROJETO OPCIONAL)
# =====================================================
def get_by_user_and_tipo(
    db: Session,
    *,
    user_id: int,
    tipo: str,
    project_id: int | None = None,
) -> RequerimentoCampo | None:
    query = db.query(RequerimentoCampo).filter(
        RequerimentoCampo.user_id == user_id,
        RequerimentoCampo.tipo == tipo,
    )

    if project_id is None:
        query = query.filter(RequerimentoCampo.project_id.is_(None))
    else:
        query = query.filter(RequerimentoCampo.project_id == project_id)

    return query.first()


# =====================================================
# CREATE / UPDATE (UPSERT)
# =====================================================
def upsert(
    db: Session,
    *,
    user_id: int,
    tipo: str,
    dados_json: dict,
    template_id: int | None,
    status: str | None,
    project_id: int | None = None,
) -> RequerimentoCampo:
    obj = get_by_user_and_tipo(
        db,
        user_id=user_id,
        tipo=tipo,
        project_id=project_id,
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


# =====================================================
# LISTAR TODOS OS REQUERIMENTOS DO USUÁRIO
# (com ou sem projeto)
# =====================================================
def list_by_user(
    db: Session,
    user_id: int,
) -> list[RequerimentoCampo]:
    return (
        db.query(RequerimentoCampo)
        .filter(RequerimentoCampo.user_id == user_id)
        .order_by(RequerimentoCampo.updated_at.desc())
        .all()
    )


# =====================================================
# VINCULAR REQUERIMENTO A UM PROJETO
# =====================================================
def attach_to_project(
    db: Session,
    *,
    requerimento_id: int,
    project_id: int,
) -> RequerimentoCampo | None:
    obj = db.query(RequerimentoCampo).filter(
        RequerimentoCampo.id == requerimento_id
    ).first()

    if not obj:
        return None

    obj.project_id = project_id
    obj.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(obj)
    return obj


# =====================================================
# DELETE (SEGURANÇA: USER + ID)
# =====================================================
def delete(
    db: Session,
    *,
    user_id: int,
    requerimento_id: int,
) -> bool:
    obj = (
        db.query(RequerimentoCampo)
        .filter(
            RequerimentoCampo.id == requerimento_id,
            RequerimentoCampo.user_id == user_id,
        )
        .first()
    )

    if not obj:
        return False

    db.delete(obj)
    db.commit()
    return True