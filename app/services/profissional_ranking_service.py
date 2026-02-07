from __future__ import annotations

from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.profissional import Profissional
from app.models.profissional_ranking import ProfissionalRanking


class ProfissionalRankingService:
    """
    Calcula ranking automático de profissionais.
    Sem APIs externas.
    Regras podem ser ajustadas facilmente.
    """

    PESO_AVALIACAO = 0.7
    PESO_EXPERIENCIA = 0.3

    @staticmethod
    def calcular_score(
        avaliacao_media: float | None,
        total_projetos: int,
    ) -> float:
        nota = avaliacao_media or 0.0
        experiencia = min(total_projetos / 10.0, 1.0)

        score = (
            (nota / 5.0) * ProfissionalRankingService.PESO_AVALIACAO
            + experiencia * ProfissionalRankingService.PESO_EXPERIENCIA
        )

        return round(score * 100.0, 2)

    @staticmethod
    def recalcular_ranking_profissional(
        db: Session,
        profissional_id: int,
    ) -> ProfissionalRanking:
        profissional = db.query(Profissional).get(profissional_id)
        if not profissional:
            raise ValueError("Profissional não encontrado.")

        score = ProfissionalRankingService.calcular_score(
            avaliacao_media=profissional.avaliacao_media,
            total_projetos=profissional.total_projetos,
        )

        ranking = (
            db.query(ProfissionalRanking)
            .filter(ProfissionalRanking.profissional_id == profissional_id)
            .first()
        )

        if not ranking:
            ranking = ProfissionalRanking(
                profissional_id=profissional_id,
                score=score,
                avaliacao_media=profissional.avaliacao_media,
                total_projetos=profissional.total_projetos,
            )
            db.add(ranking)
        else:
            ranking.score = score
            ranking.avaliacao_media = profissional.avaliacao_media
            ranking.total_projetos = profissional.total_projetos
            ranking.calculado_em = datetime.utcnow()

        db.commit()
        db.refresh(ranking)
        return ranking

    @staticmethod
    def recalcular_todos(db: Session) -> None:
        profissionais = db.query(Profissional).filter(Profissional.ativo.is_(True)).all()
        for prof in profissionais:
            ProfissionalRankingService.recalcular_ranking_profissional(db, prof.id)

    @staticmethod
    def melhores_profissionais(
        db: Session,
        limit: int = 5,
    ) -> list[ProfissionalRanking]:
        return (
            db.query(ProfissionalRanking)
            .filter(ProfissionalRanking.ativo.is_(True))
            .order_by(ProfissionalRanking.score.desc())
            .limit(limit)
            .all()
        )
