from fastapi import HTTPException

from app.models.project import Project


class ProjectStatusGuardService:
    """
    Travas duras de status do projeto.
    """

    STATUS_BLOQUEADOS_PARA_EDICAO = {
        "FINALIZADO",
        "ARQUIVADO",
    }

    @staticmethod
    def bloquear_edicao(project: Project):
        if project.status.upper() in ProjectStatusGuardService.STATUS_BLOQUEADOS_PARA_EDICAO:
            raise HTTPException(
                status_code=409,
                detail="Projeto não pode ser alterado neste status.",
            )
