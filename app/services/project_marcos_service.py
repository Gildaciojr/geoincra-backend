from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.project_status import ProjectStatus
from app.services.project_automacao_service import ProjectAutomacaoService
from app.services.pagamento_automacao_service import PagamentoAutomacaoService
from app.schemas.project_status import ProjectStatusCreate


@dataclass(frozen=True)
class _Motivo:
    codigo: str
    descricao: str


class ProjectMarcosService:
    """
    Regras de liberação por marco (SEM APIs):
    - Exemplo: se APROVADO_TECNICAMENTE e NÃO bloqueado por pagamento -> PRONTO_PARA_SIGEF
    """

    STATUS_PRONTO_PARA_SIGEF = "PRONTO_PARA_SIGEF"

    @staticmethod
    def _now_utc() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _status_atual(db: Session, project_id: int) -> ProjectStatus | None:
        return (
            db.query(ProjectStatus)
            .filter(ProjectStatus.project_id == project_id, ProjectStatus.ativo.is_(True))
            .first()
        )

    @staticmethod
    def avaliar_avanco_para_sigef(
        db: Session,
        project_id: int,
    ) -> Tuple[bool, Optional[str], Optional[str], Optional[str], List[_Motivo]]:
        """
        Retorna:
        - pode_avancar
        - status_atual
        - status_sugerido
        - descricao
        - motivos
        """
        motivos: List[_Motivo] = []

        # 1) Antes de avaliar, roda automação de atraso local (para refletir bloqueios reais)
        PagamentoAutomacaoService.marcar_atrasados(db, project_id=project_id)

        # 2) Diagnóstico do status (bloqueios e situação atual)
        status_sugerido_automacao, desc, bloqueado, bloqueio_motivo, motivos_auto = (
            ProjectAutomacaoService.diagnosticar_status(db, project_id)
        )

        atual = ProjectMarcosService._status_atual(db, project_id)
        status_atual = atual.status if atual else None

        for m in motivos_auto:
            motivos.append(_Motivo(codigo=m.codigo, descricao=m.descricao))

        if bloqueado:
            motivos.append(
                _Motivo(
                    codigo="BLOQUEIO_FLUXO",
                    descricao=f"Fluxo bloqueado: {bloqueio_motivo or 'motivo não informado'}.",
                )
            )
            return False, status_atual, None, "Não pode avançar: há bloqueios no fluxo.", motivos

        # Regra: precisa estar APROVADO_TECNICAMENTE pelo motor de documentos técnicos
        if status_sugerido_automacao != ProjectAutomacaoService.STATUS_APROVADO_TECNICAMENTE:
            motivos.append(
                _Motivo(
                    codigo="NAO_APROVADO_TECNICAMENTE",
                    descricao=(
                        "Para avançar, o projeto precisa estar aprovado tecnicamente "
                        "(documentos técnicos atuais aprovados)."
                    ),
                )
            )
            return (
                False,
                status_atual,
                None,
                "Não pode avançar: ainda não está aprovado tecnicamente.",
                motivos,
            )

        # OK: pode avançar
        motivos.append(
            _Motivo(
                codigo="APTO_PARA_SIGEF",
                descricao="Projeto aprovado tecnicamente e sem bloqueios. Pode avançar para PRONTO_PARA_SIGEF.",
            )
        )
        return True, status_atual, ProjectMarcosService.STATUS_PRONTO_PARA_SIGEF, "Apto para envio SIGEF (quando integrar).", motivos

    @staticmethod
    def aplicar_avanco_para_sigef(
        db: Session,
        project_id: int,
    ) -> Tuple[bool, Optional[str], List[_Motivo]]:
        pode, _, sugerido, desc, motivos = ProjectMarcosService.avaliar_avanco_para_sigef(db, project_id)
        if not pode or not sugerido:
            return False, None, motivos

        payload = ProjectStatusCreate(
            status=sugerido,
            descricao=desc,
            definido_automaticamente=True,
            definido_por_usuario_id=None,
        )

        from app.crud.project_status_crud import definir_status_projeto

        definir_status_projeto(db, project_id, payload)
        return True, sugerido, motivos
