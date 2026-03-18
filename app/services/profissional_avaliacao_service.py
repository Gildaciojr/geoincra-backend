from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.profissional import Profissional
from app.models.profissional_avaliacao import ProfissionalAvaliacao


class ProfissionalAvaliacaoService:
    """
    Serviço isolado para métricas e regras futuras.
    """

    @staticmethod
    def recalcular_metricas(
        db: Session,
        profissional_id: int,
    ) -> None:
        media, total = (
            db.query(
                func.avg(ProfissionalAvaliacao.nota),
                func.count(ProfissionalAvaliacao.id),
            )
            .filter(ProfissionalAvaliacao.profissional_id == profissional_id)
            .one()
        )

        profissional = db.query(Profissional).get(profissional_id)
        if not profissional:
            return

        # 🔥 CORREÇÃO: usar campos do MODEL
        profissional.rating_medio = (
            round(float(media), 2) if media else 0.0
        )

        profissional.total_servicos = int(total)

        db.commit()