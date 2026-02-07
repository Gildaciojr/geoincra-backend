from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.avaliacao_profissional import AvaliacaoProfissional
from app.models.profissional import Profissional
from app.schemas.avaliacao_profissional import AvaliacaoProfissionalCreate


# =========================================================
# CREATE
# =========================================================
def criar_avaliacao(
    db: Session,
    project_id: int,
    data: AvaliacaoProfissionalCreate,
) -> AvaliacaoProfissional:
    existente = (
        db.query(AvaliacaoProfissional)
        .filter(
            AvaliacaoProfissional.project_id == project_id,
            AvaliacaoProfissional.profissional_id == data.profissional_id,
        )
        .first()
    )
    if existente:
        raise ValueError("Este profissional já foi avaliado neste projeto.")

    avaliacao = AvaliacaoProfissional(
        project_id=project_id,
        profissional_id=data.profissional_id,
        nota=data.nota,
        comentario=data.comentario,
    )

    db.add(avaliacao)
    db.commit()
    db.refresh(avaliacao)

    _recalcular_rating_profissional(db, data.profissional_id)

    return avaliacao


# =========================================================
# LIST
# =========================================================
def listar_avaliacoes_profissional(
    db: Session,
    profissional_id: int,
) -> list[AvaliacaoProfissional]:
    return (
        db.query(AvaliacaoProfissional)
        .filter(AvaliacaoProfissional.profissional_id == profissional_id)
        .order_by(AvaliacaoProfissional.created_at.desc())
        .all()
    )


# =========================================================
# AUX
# =========================================================
def _recalcular_rating_profissional(
    db: Session,
    profissional_id: int,
):
    profissional = (
        db.query(Profissional)
        .filter(Profissional.id == profissional_id)
        .first()
    )
    if not profissional:
        return

    media = (
        db.query(func.avg(AvaliacaoProfissional.nota))
        .filter(AvaliacaoProfissional.profissional_id == profissional_id)
        .scalar()
    )

    total = (
        db.query(func.count(AvaliacaoProfissional.id))
        .filter(AvaliacaoProfissional.profissional_id == profissional_id)
        .scalar()
    )

    profissional.rating_medio = round(float(media or 0), 2)
    profissional.total_servicos = int(total or 0)

    db.commit()
