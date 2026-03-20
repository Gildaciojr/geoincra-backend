from datetime import datetime
from sqlalchemy.orm import Session

from app.models.timeline import TimelineEntry


class TimelineService:

    @staticmethod
    def registrar_evento(
        db: Session,
        project_id: int,
        titulo: str,
        descricao: str | None = None,
        status: str | None = None,
    ):
        try:
            entry = TimelineEntry(
                project_id=project_id,
                titulo=titulo,
                descricao=descricao,
                status=status,
                created_at=datetime.utcnow(),
            )

            db.add(entry)

            # 🔥 NÃO COMMIT AQUI
            return entry

        except Exception as e:
            print(f"⚠️ Falha ao registrar timeline: {str(e)}")
            return None