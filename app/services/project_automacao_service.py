from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.project_status import ProjectStatus
from app.models.pagamento import Pagamento
from app.models.documento_tecnico import DocumentoTecnico

from app.schemas.project_status import ProjectStatusCreate
from app.services.timeline_service import TimelineService


@dataclass(frozen=True)
class _Motivo:
    codigo: str
    descricao: str


class ProjectAutomacaoService:
    """
    Automação do fluxo do projeto (SEM APIs externas).
    Objetivo:
    - Ler dados do core (pagamentos + documentos técnicos)
    - Sugerir status do projeto
    - Aplicar status automaticamente (histórico), se necessário

    Regras (ordem de prioridade):
    1) Bloqueio por pagamento (PENDENTE/ATRASADO e bloqueia_fluxo=True)
    2) Documentos técnicos com pendências (CORRIGIR/REPROVADO) nas versões atuais
    3) Documentos técnicos em análise (EM_ANALISE)
    4) Documentos técnicos aprovados (APROVADO) -> APROVADO_TECNICAMENTE
    5) Caso não haja documentos técnicos atuais -> DOCUMENTOS_NAO_ENVIADOS
    """

    STATUS_PAGAMENTO_ATRASADO = "PAGAMENTO_ATRASADO"
    STATUS_PAGAMENTO_PENDENTE = "PAGAMENTO_PENDENTE"

    STATUS_DOCUMENTOS_NAO_ENVIADOS = "DOCUMENTOS_NAO_ENVIADOS"
    STATUS_DOCUMENTOS_EM_ANALISE = "DOCUMENTOS_EM_ANALISE"
    STATUS_AJUSTES_SOLICITADOS = "AJUSTES_SOLICITADOS"
    STATUS_APROVADO_TECNICAMENTE = "APROVADO_TECNICAMENTE"

    DOC_APROVADO = "APROVADO"
    DOC_CORRIGIR = "CORRIGIR"
    DOC_REPROVADO = "REPROVADO"
    DOC_EM_ANALISE = "EM_ANALISE"
    DOC_RASCUNHO = "RASCUNHO"

    @staticmethod
    def _now_utc() -> datetime:
        return datetime.now(timezone.utc)

    @staticmethod
    def _get_project(db: Session, project_id: int) -> Project | None:
        return db.query(Project).filter(Project.id == project_id).first()

    @staticmethod
    def _status_atual(db: Session, project_id: int) -> ProjectStatus | None:
        return (
            db.query(ProjectStatus)
            .filter(ProjectStatus.project_id == project_id, ProjectStatus.ativo.is_(True))
            .first()
        )

    @staticmethod
    def _pagamentos_bloqueadores(db: Session, project_id: int) -> List[Pagamento]:
        return (
            db.query(Pagamento)
            .filter(
                Pagamento.project_id == project_id,
                Pagamento.bloqueia_fluxo.is_(True),
                Pagamento.status != "PAGO",
                Pagamento.status != "CANCELADO",
            )
            .order_by(Pagamento.data_vencimento.asc())
            .all()
        )

    @staticmethod
    def _documentos_tecnicos_atuais_do_projeto(db: Session, project_id: int) -> List[DocumentoTecnico]:
        from app.models.imovel import Imovel

        return (
            db.query(DocumentoTecnico)
            .join(Imovel, Imovel.id == DocumentoTecnico.imovel_id)
            .filter(
                Imovel.project_id == project_id,
                DocumentoTecnico.is_versao_atual.is_(True),
            )
            .order_by(DocumentoTecnico.updated_at.desc())
            .all()
        )

    @staticmethod
    def diagnosticar_status(db: Session, project_id: int) -> Tuple[str, str, bool, Optional[str], List[_Motivo]]:
        project = ProjectAutomacaoService._get_project(db, project_id)
        if not project:
            raise ValueError("Projeto não encontrado.")

        motivos: List[_Motivo] = []

        now = ProjectAutomacaoService._now_utc()
        pag_bloq = ProjectAutomacaoService._pagamentos_bloqueadores(db, project_id)

        if pag_bloq:
            atrasados = []
            pendentes = []

            for p in pag_bloq:
                dv = p.data_vencimento
                if dv.tzinfo is None:
                    dv = dv.replace(tzinfo=timezone.utc)

                if dv < now and p.status == "PENDENTE":
                    atrasados.append(p)
                else:
                    pendentes.append(p)

            if atrasados:
                motivos.append(_Motivo("PAGAMENTO_ATRASADO", f"Existe(m) {len(atrasados)} pagamento(s) bloqueador(es) em atraso."))
                return (
                    ProjectAutomacaoService.STATUS_PAGAMENTO_ATRASADO,
                    "Processo bloqueado: pagamento(s) em atraso.",
                    True,
                    "Pagamento atrasado",
                    motivos,
                )

            motivos.append(_Motivo("PAGAMENTO_PENDENTE", f"Existe(m) {len(pendentes)} pagamento(s) bloqueador(es) pendente(s)."))
            return (
                ProjectAutomacaoService.STATUS_PAGAMENTO_PENDENTE,
                "Processo bloqueado: pagamento(s) pendente(s).",
                True,
                "Pagamento pendente",
                motivos,
            )

        docs = ProjectAutomacaoService._documentos_tecnicos_atuais_do_projeto(db, project_id)

        if not docs:
            motivos.append(_Motivo("SEM_DOCUMENTOS_TECNICOS", "Nenhum documento técnico encontrado."))
            return (
                ProjectAutomacaoService.STATUS_DOCUMENTOS_NAO_ENVIADOS,
                "Aguardando envio dos documentos técnicos.",
                False,
                None,
                motivos,
            )

        qtd_aprov = qtd_analise = qtd_corrigir = qtd_reprovado = qtd_rascunho = 0

        for d in docs:
            st = (d.status_tecnico or "").upper().strip()
            if st == ProjectAutomacaoService.DOC_APROVADO:
                qtd_aprov += 1
            elif st == ProjectAutomacaoService.DOC_EM_ANALISE:
                qtd_analise += 1
            elif st == ProjectAutomacaoService.DOC_CORRIGIR:
                qtd_corrigir += 1
            elif st == ProjectAutomacaoService.DOC_REPROVADO:
                qtd_reprovado += 1
            else:
                qtd_rascunho += 1

        if qtd_reprovado > 0:
            motivos.append(_Motivo("DOCS_REPROVADOS", f"Há {qtd_reprovado} documentos reprovados."))
            return (ProjectAutomacaoService.STATUS_AJUSTES_SOLICITADOS, "Ajustes solicitados.", False, None, motivos)

        if qtd_corrigir > 0:
            motivos.append(_Motivo("DOCS_CORRIGIR", f"Há {qtd_corrigir} documentos pendentes de correção."))
            return (ProjectAutomacaoService.STATUS_AJUSTES_SOLICITADOS, "Ajustes solicitados.", False, None, motivos)

        if qtd_analise > 0:
            motivos.append(_Motivo("DOCS_EM_ANALISE", f"Há {qtd_analise} documentos em análise."))
            return (ProjectAutomacaoService.STATUS_DOCUMENTOS_EM_ANALISE, "Documentos em análise.", False, None, motivos)

        if qtd_aprov == len(docs):
            motivos.append(_Motivo("DOCS_APROVADOS", "Todos os documentos aprovados."))
            return (ProjectAutomacaoService.STATUS_APROVADO_TECNICAMENTE, "Projeto aprovado tecnicamente.", False, None, motivos)

        motivos.append(_Motivo("DOCS_RASCUNHO", "Documentos em rascunho."))
        return (ProjectAutomacaoService.STATUS_DOCUMENTOS_EM_ANALISE, "Documentos em rascunho.", False, None, motivos)

    @staticmethod
    def aplicar_status_automatico(db: Session, project_id: int) -> Tuple[str, bool, List[_Motivo]]:
        status_sugerido, desc, _, _, motivos = ProjectAutomacaoService.diagnosticar_status(db, project_id)

        atual = ProjectAutomacaoService._status_atual(db, project_id)
        if atual and (atual.status or "").upper().strip() == status_sugerido:
            return status_sugerido, False, motivos

        payload = ProjectStatusCreate(
            status=status_sugerido,
            descricao=desc,
            definido_automaticamente=True,
            definido_por_usuario_id=None,
        )

        from app.crud.project_status_crud import definir_status_projeto

        definir_status_projeto(db, project_id, payload)

        # 🔵 REGISTRO AUTOMÁTICO NA TIMELINE
        TimelineService.registrar_evento(
            db=db,
            project_id=project_id,
            titulo=f"Status do projeto atualizado automaticamente: {status_sugerido}",
            descricao=desc,
            status=status_sugerido,
        )

        return status_sugerido, True, motivos
