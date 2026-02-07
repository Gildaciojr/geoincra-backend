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

    # Status padronizados do projeto (tabela project_status.status)
    STATUS_PAGAMENTO_ATRASADO = "PAGAMENTO_ATRASADO"
    STATUS_PAGAMENTO_PENDENTE = "PAGAMENTO_PENDENTE"

    STATUS_DOCUMENTOS_NAO_ENVIADOS = "DOCUMENTOS_NAO_ENVIADOS"
    STATUS_DOCUMENTOS_EM_ANALISE = "DOCUMENTOS_EM_ANALISE"
    STATUS_AJUSTES_SOLICITADOS = "AJUSTES_SOLICITADOS"
    STATUS_APROVADO_TECNICAMENTE = "APROVADO_TECNICAMENTE"

    # Status técnico dos documentos (DocumentoTecnico.status_tecnico)
    DOC_APROVADO = "APROVADO"
    DOC_CORRIGIR = "CORRIGIR"
    DOC_REPROVADO = "REPROVADO"
    DOC_EM_ANALISE = "EM_ANALISE"
    DOC_RASCUNHO = "RASCUNHO"

    @staticmethod
    def _now_utc() -> datetime:
        return datetime.now(timezone.utc)

    # =========================================================
    # CONSULTAS
    # =========================================================

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
        """
        Retorna pagamentos do projeto que bloqueiam o fluxo e não estão pagos.
        """
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
        """
        DocumentoTecnico é por imóvel. Aqui buscamos por todos os imóveis do project via join.
        Para evitar depender de FK no DocumentoTecnico->Project, usamos o caminho:
        DocumentoTecnico.imovel_id -> Imovel.project_id
        """
        # Import local para evitar ciclo
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

    # =========================================================
    # MOTOR DE DECISÃO
    # =========================================================

    @staticmethod
    def diagnosticar_status(db: Session, project_id: int) -> Tuple[str, str, bool, Optional[str], List[_Motivo]]:
        """
        Retorna:
        - status_sugerido
        - descricao_status
        - bloqueado
        - bloqueio_motivo
        - motivos
        """
        project = ProjectAutomacaoService._get_project(db, project_id)
        if not project:
            raise ValueError("Projeto não encontrado.")

        motivos: List[_Motivo] = []

        # ----------------------------
        # 1) Pagamentos (bloqueio)
        # ----------------------------
        now = ProjectAutomacaoService._now_utc()
        pag_bloq = ProjectAutomacaoService._pagamentos_bloqueadores(db, project_id)

        if pag_bloq:
            atrasados = []
            pendentes = []

            for p in pag_bloq:
                # data_vencimento pode vir naive; comparamos convertendo para UTC
                dv = p.data_vencimento
                if dv.tzinfo is None:
                    dv = dv.replace(tzinfo=timezone.utc)

                if dv < now and p.status == "PENDENTE":
                    atrasados.append(p)
                else:
                    pendentes.append(p)

            if atrasados:
                motivos.append(
                    _Motivo(
                        codigo="PAGAMENTO_ATRASADO",
                        descricao=f"Existe(m) {len(atrasados)} pagamento(s) bloqueador(es) em atraso.",
                    )
                )
                return (
                    ProjectAutomacaoService.STATUS_PAGAMENTO_ATRASADO,
                    "Processo bloqueado: pagamento(s) em atraso.",
                    True,
                    "Pagamento atrasado",
                    motivos,
                )

            motivos.append(
                _Motivo(
                    codigo="PAGAMENTO_PENDENTE",
                    descricao=f"Existe(m) {len(pendentes)} pagamento(s) bloqueador(es) pendente(s).",
                )
            )
            return (
                ProjectAutomacaoService.STATUS_PAGAMENTO_PENDENTE,
                "Processo bloqueado: pagamento(s) pendente(s).",
                True,
                "Pagamento pendente",
                motivos,
            )

        # ----------------------------
        # 2) Documentos Técnicos
        # ----------------------------
        docs = ProjectAutomacaoService._documentos_tecnicos_atuais_do_projeto(db, project_id)

        if not docs:
            motivos.append(
                _Motivo(
                    codigo="SEM_DOCUMENTOS_TECNICOS",
                    descricao="Nenhum documento técnico (versão atual) encontrado para os imóveis do projeto.",
                )
            )
            return (
                ProjectAutomacaoService.STATUS_DOCUMENTOS_NAO_ENVIADOS,
                "Aguardando envio/geração dos documentos técnicos.",
                False,
                None,
                motivos,
            )

        # Contagem por status técnico
        qtd_aprov = 0
        qtd_analise = 0
        qtd_corrigir = 0
        qtd_reprovado = 0
        qtd_rascunho = 0

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

        # Pendências têm prioridade
        if qtd_reprovado > 0:
            motivos.append(
                _Motivo(
                    codigo="DOCS_REPROVADOS",
                    descricao=f"Há {qtd_reprovado} documento(s) técnico(s) reprovado(s) nas versões atuais.",
                )
            )
            return (
                ProjectAutomacaoService.STATUS_AJUSTES_SOLICITADOS,
                "Ajustes solicitados: documentos técnicos reprovados.",
                False,
                None,
                motivos,
            )

        if qtd_corrigir > 0:
            motivos.append(
                _Motivo(
                    codigo="DOCS_CORRIGIR",
                    descricao=f"Há {qtd_corrigir} documento(s) técnico(s) com status CORRIGIR nas versões atuais.",
                )
            )
            return (
                ProjectAutomacaoService.STATUS_AJUSTES_SOLICITADOS,
                "Ajustes solicitados: documentos técnicos pendentes para correção.",
                False,
                None,
                motivos,
            )

        if qtd_analise > 0:
            motivos.append(
                _Motivo(
                    codigo="DOCS_EM_ANALISE",
                    descricao=f"Há {qtd_analise} documento(s) técnico(s) em análise nas versões atuais.",
                )
            )
            return (
                ProjectAutomacaoService.STATUS_DOCUMENTOS_EM_ANALISE,
                "Documentos técnicos em análise.",
                False,
                None,
                motivos,
            )

        # Se chegou aqui: sem pendências e sem análise
        if qtd_aprov > 0 and (qtd_aprov == len(docs)):
            motivos.append(
                _Motivo(
                    codigo="DOCS_APROVADOS",
                    descricao=f"Todos os {qtd_aprov} documentos técnicos (versão atual) estão aprovados.",
                )
            )
            return (
                ProjectAutomacaoService.STATUS_APROVADO_TECNICAMENTE,
                "Projeto aprovado tecnicamente com base nos documentos técnicos atuais.",
                False,
                None,
                motivos,
            )

        # Caso híbrido (ex.: rascunho)
        motivos.append(
            _Motivo(
                codigo="DOCS_RASCUNHO",
                descricao=f"Existem documentos técnicos em rascunho/indefinidos ({qtd_rascunho}).",
            )
        )
        return (
            ProjectAutomacaoService.STATUS_DOCUMENTOS_EM_ANALISE,
            "Documentos técnicos ainda não finalizados (rascunho/indefinido).",
            False,
            None,
            motivos,
        )

    # =========================================================
    # APLICAR STATUS
    # =========================================================

    @staticmethod
    def aplicar_status_automatico(db: Session, project_id: int) -> Tuple[str, bool, List[_Motivo]]:
        """
        Calcula o status sugerido e grava em project_status (histórico),
        somente se diferente do status atual ativo.

        Retorna:
        - status_aplicado
        - criado_novo_status (True/False)
        - motivos
        """
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

        # Import local para evitar circular
        from app.crud.project_status_crud import definir_status_projeto

        definir_status_projeto(db, project_id, payload)

        return status_sugerido, True, motivos
