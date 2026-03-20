from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.project_status import ProjectStatus
from app.models.documento_tecnico import DocumentoTecnico
from app.models.imovel import Imovel
from app.models.timeline import TimelineEntry
from app.crud.project_status_crud import definir_status_projeto
from app.schemas.project_status import ProjectStatusCreate


class ProjectFluxoService:
    """
    Serviço responsável por controlar o fluxo automático do projeto
    com base no estado dos documentos técnicos.

    Atua sobre:
    - ProjectStatus
    - Timeline
    """

    # =========================================================
    # STATUS POSSÍVEIS DO PROJETO
    # =========================================================

    STATUS_CADASTRADO = "CADASTRADO"
    STATUS_DOCUMENTOS_EM_ANALISE = "DOCUMENTOS_EM_ANALISE"
    STATUS_AJUSTES_SOLICITADOS = "AJUSTES_SOLICITADOS"
    STATUS_APROVADO_TECNICAMENTE = "APROVADO_TECNICAMENTE"
    STATUS_PRONTO_PARA_SIGEF = "PRONTO_PARA_SIGEF"
    STATUS_FINALIZADO = "FINALIZADO"

    # =========================================================
    # STATUS TÉCNICOS DOS DOCUMENTOS
    # =========================================================

    DOC_APROVADO = "APROVADO"
    DOC_CORRIGIR = "CORRIGIR"
    DOC_REPROVADO = "REPROVADO"
    DOC_EM_ANALISE = "EM_ANALISE"
    DOC_RASCUNHO = "RASCUNHO"

    @staticmethod
    def avaliar_fluxo_projeto(
        db: Session,
        project_id: int,
        definido_por_usuario_id: int | None = None,
    ) -> ProjectStatus:
        """
        Avalia o estado atual do projeto e define automaticamente
        o status adequado com base nos documentos técnicos.
        """

        project: Project | None = (
            db.query(Project)
            .filter(Project.id == project_id)
            .first()
        )

        if not project:
            raise ValueError("Projeto não encontrado.")

        documentos: List[DocumentoTecnico] = (
            db.query(DocumentoTecnico)
            .join(Imovel, Imovel.id == DocumentoTecnico.imovel_id)
            .filter(Imovel.project_id == project_id)
            .filter(DocumentoTecnico.is_versao_atual.is_(True))
            .all()
        )

        if not documentos:
            return ProjectFluxoService._definir_status(
                db=db,
                project_id=project_id,
                status=ProjectFluxoService.STATUS_CADASTRADO,
                descricao="Projeto cadastrado. Nenhum documento técnico anexado.",
                definido_por_usuario_id=definido_por_usuario_id,
            )

        total = len(documentos)
        aprovados = 0
        corrigir = 0
        reprovados = 0
        em_analise = 0

        for doc in documentos:
            status_doc = (doc.status_tecnico or "").upper().strip()

            if status_doc == ProjectFluxoService.DOC_APROVADO:
                aprovados += 1
            elif status_doc == ProjectFluxoService.DOC_CORRIGIR:
                corrigir += 1
            elif status_doc == ProjectFluxoService.DOC_REPROVADO:
                reprovados += 1
            elif status_doc in (
                ProjectFluxoService.DOC_EM_ANALISE,
                ProjectFluxoService.DOC_RASCUNHO,
            ):
                em_analise += 1

        if reprovados > 0:
            return ProjectFluxoService._definir_status(
                db=db,
                project_id=project_id,
                status=ProjectFluxoService.STATUS_AJUSTES_SOLICITADOS,
                descricao="Documentos técnicos reprovados. Ajustes obrigatórios.",
                definido_por_usuario_id=definido_por_usuario_id,
            )

        if corrigir > 0:
            return ProjectFluxoService._definir_status(
                db=db,
                project_id=project_id,
                status=ProjectFluxoService.STATUS_AJUSTES_SOLICITADOS,
                descricao="Documentos técnicos pendentes de correção.",
                definido_por_usuario_id=definido_por_usuario_id,
            )

        if em_analise > 0:
            return ProjectFluxoService._definir_status(
                db=db,
                project_id=project_id,
                status=ProjectFluxoService.STATUS_DOCUMENTOS_EM_ANALISE,
                descricao="Documentos técnicos em análise.",
                definido_por_usuario_id=definido_por_usuario_id,
            )

        if aprovados == total:
            return ProjectFluxoService._definir_status(
                db=db,
                project_id=project_id,
                status=ProjectFluxoService.STATUS_APROVADO_TECNICAMENTE,
                descricao="Todos os documentos técnicos foram aprovados.",
                definido_por_usuario_id=definido_por_usuario_id,
            )

        return ProjectFluxoService._definir_status(
            db=db,
            project_id=project_id,
            status=ProjectFluxoService.STATUS_DOCUMENTOS_EM_ANALISE,
            descricao="Estado técnico indefinido. Revisão necessária.",
            definido_por_usuario_id=definido_por_usuario_id,
        )

    @staticmethod
    def _definir_status(
        db: Session,
        project_id: int,
        status: str,
        descricao: str,
        definido_por_usuario_id: int | None,
    ) -> ProjectStatus:
        payload = ProjectStatusCreate(
            status=status,
            descricao=descricao,
            definido_automaticamente=True,
            definido_por_usuario_id=definido_por_usuario_id,
        )

        status_obj = definir_status_projeto(
            db=db,
            project_id=project_id,
            data=payload,
        )

        timeline = TimelineEntry(
            project_id=project_id,
            titulo=f"Status do projeto atualizado: {status}",
            descricao=descricao,
            status=status,
            created_at=datetime.utcnow(),
        )

        db.add(timeline)
        db.commit()

        return status_obj