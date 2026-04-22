from datetime import datetime
from sqlalchemy.orm import Session

from app.models.timeline import TimelineEntry


# =========================================================
# 🔒 STATUS VÁLIDOS (PADRÃO DO SISTEMA)
# =========================================================
STATUS_VALIDOS = ["Pendente", "Em Andamento", "Concluído"]


class TimelineService:

    @staticmethod
    def registrar_evento(
        db: Session,
        project_id: int,
        titulo: str,
        descricao: str | None = None,
        status: str | None = None,
        etapa: str | None = None,
        created_by_user_id: int | None = None,
    ):
        """
        🔥 IMPORTANTE:
        Este método NÃO realiza commit.

        O chamador é responsável por:
            - db.commit()
            - db.rollback() em caso de erro

        Ideal para uso em pipelines (OCR, geração de documentos, etc.)
        """

        try:

            # =========================================================
            # 🧼 SANITIZAÇÃO DE DADOS
            # =========================================================
            titulo = titulo.strip() if titulo else None
            descricao = descricao.strip() if descricao else None
            status = status.strip() if status else None
            etapa = etapa.strip() if etapa else None

            if not titulo:
                raise ValueError("Título da timeline é obrigatório")

            # =========================================================
            # 🔍 VALIDAÇÃO DE STATUS
            # =========================================================
            if status and status not in STATUS_VALIDOS:
                raise ValueError(
                    f"Status inválido: '{status}'. Permitidos: {STATUS_VALIDOS}"
                )

            # =========================================================
            # 🏗️ CRIAÇÃO DA ENTRY
            # =========================================================
            entry = TimelineEntry(
                project_id=project_id,
                created_by_user_id=created_by_user_id,
                titulo=titulo,
                descricao=descricao,
                status=status,
                etapa=etapa,
                created_at=datetime.utcnow(),
            )

            db.add(entry)

            return entry

        except Exception as e:
            print(
                f"⚠️ Falha ao registrar timeline | "
                f"project_id={project_id} | titulo={titulo} | erro={str(e)}"
            )
            return None