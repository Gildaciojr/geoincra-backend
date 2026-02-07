from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.profissional import Profissional
from app.models.avaliacao_profissional import AvaliacaoProfissional
from app.schemas.profissional_avaliacao import ProfissionalAvaliacaoCreate


def criar_avaliacao_profissional(
    db: Session,
    profissional_id: int,
    data: ProfissionalAvaliacaoCreate,
) -> AvaliacaoProfissional:
    profissional = db.query(Profissional).get(profissional_id)
    if not profissional:
        raise ValueError("Profissional não encontrado.")

    avaliacao = AvaliacaoProfissional(
        profissional_id=profissional_id,
        project_id=data.project_id,
        nota=data.nota,
        comentario=data.comentario,
        origem=data.origem,
    )

    db.add(avaliacao)
    db.commit()
    db.refresh(avaliacao)

    _recalcular_metricas_profissional(db, profissional_id)

    return avaliacao


def listar_avaliacoes_por_profissional(
    db: Session,
    profissional_id: int,
) -> list[AvaliacaoProfissional]:
    return (
        db.query(AvaliacaoProfissional)
        .filter(AvaliacaoProfissional.profissional_id == profissional_id)
        .order_by(AvaliacaoProfissional.created_at.desc())
        .all()
    )


def get_avaliacao(
    db: Session,
    avaliacao_id: int,
) -> AvaliacaoProfissional | None:
    return (
        db.query(AvaliacaoProfissional)
        .filter(AvaliacaoProfissional.id == avaliacao_id)
        .first()
    )


def _recalcular_metricas_profissional(db: Session, profissional_id: int) -> None:
    media, total = (
        db.query(
            func.avg(AvaliacaoProfissional.nota),
            func.count(AvaliacaoProfissional.id),
        )
        .filter(AvaliacaoProfissional.profissional_id == profissional_id)
        .one()
    )

    profissional = db.query(Profissional).get(profissional_id)
    if not profissional:
        return

    profissional.rating_medio = round(float(media), 2) if media else 0.0
    profissional.total_servicos = int(total)

    db.commit()
