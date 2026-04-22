from sqlalchemy.orm import Session
from app.models.timeline import TimelineEntry
from app.schemas.timeline import TimelineCreate


# =========================================================
# 🔒 STATUS VÁLIDOS (PADRÃO DO SISTEMA)
# =========================================================
STATUS_VALIDOS = ["Pendente", "Em Andamento", "Concluído"]


def create_timeline_entry(db: Session, project_id: int, data: TimelineCreate):
    try:

        # =========================================================
        # 🔍 VALIDAÇÃO DE STATUS
        # =========================================================
        status = data.status.strip() if data.status else None

        if status and status not in STATUS_VALIDOS:
            raise ValueError(
                f"Status inválido: '{status}'. Permitidos: {STATUS_VALIDOS}"
            )

        # =========================================================
        # 🧼 SANITIZAÇÃO DE CAMPOS
        # =========================================================
        titulo = data.titulo.strip()
        descricao = data.descricao.strip() if data.descricao else None
        etapa = data.etapa.strip() if data.etapa else None

        # =========================================================
        # 🏗️ CRIAÇÃO DA ENTRY
        # =========================================================
        entry = TimelineEntry(
            project_id=project_id,
            created_by_user_id=data.created_by_user_id,
            titulo=titulo,
            descricao=descricao,
            status=status,
            etapa=etapa,
        )

        db.add(entry)
        db.commit()
        db.refresh(entry)

        return entry

    except Exception as e:
        db.rollback()
        raise e


def list_timeline_for_project(db: Session, project_id: int):
    return (
        db.query(TimelineEntry)
        .filter(TimelineEntry.project_id == project_id)
        .order_by(TimelineEntry.created_at.desc())
        .all()
    )


def get_entry_by_id(db: Session, entry_id: int):
    return db.query(TimelineEntry).filter(TimelineEntry.id == entry_id).first()


def delete_entry(db: Session, entry_id: int):
    entry = get_entry_by_id(db, entry_id)

    if not entry:
        return False

    try:
        db.delete(entry)
        db.commit()
        return True

    except Exception:
        db.rollback()
        raise