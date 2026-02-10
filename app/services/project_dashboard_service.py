from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.project_status import ProjectStatus
from app.services.project_automacao_service import ProjectAutomacaoService
from app.services.project_marcos_service import ProjectMarcosService
from app.services.pagamento_service import PagamentoService


class ProjectDashboardService:

    @staticmethod
    def obter_diagnostico(db: Session, project_id: int) -> dict:

        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise ValueError("Projeto não encontrado.")

        # ================================
        # STATUS AUTOMÁTICO
        # ================================
        status_sugerido, descricao, bloqueado, motivo_bloqueio, motivos = (
            ProjectAutomacaoService.diagnosticar_status(db, project_id)
        )

        # ================================
        # STATUS ATUAL ATIVO
        # ================================
        status_atual = (
            db.query(ProjectStatus)
            .filter(ProjectStatus.project_id == project_id, ProjectStatus.ativo.is_(True))
            .first()
        )

        # ================================
        # LIBERAÇÃO SIGEF
        # ================================
        pode_avancar, status_atual_marco, sugerido_marco, desc_marco, motivos_marco = (
            ProjectMarcosService.avaliar_avanco_para_sigef(db, project_id)
        )

        # ================================
        # FINANCEIRO
        # ================================
        pagamentos = project.pagamentos

        total_financeiro = sum(p.total for p in pagamentos)
        pago = 0.0

        for p in pagamentos:
            pct = PagamentoService.obter_percentual_pago(db, p.id)
            pago += (p.total * pct) / 100.0

        percentual_pago = 0.0
        if total_financeiro > 0:
            percentual_pago = round((pago / total_financeiro) * 100.0, 2)

        return {
            "project_id": project_id,
            "project_name": project.name,

            "status_atual": status_atual.status if status_atual else None,
            "status_sugerido": status_sugerido,
            "descricao_status": descricao,

            "bloqueado": bloqueado,
            "motivo_bloqueio": motivo_bloqueio,

            "financeiro": {
                "total": total_financeiro,
                "percentual_pago": percentual_pago,
            },

            "fluxo": {
                "pode_avancar_sigef": pode_avancar,
                "status_sugerido_marco": sugerido_marco,
                "descricao_marco": desc_marco,
            },

            "motivos": [m.codigo for m in motivos],
            "motivos_marco": [m.codigo for m in motivos_marco],
        }
