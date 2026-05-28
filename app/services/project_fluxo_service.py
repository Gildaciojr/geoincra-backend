from __future__ import annotations

import logging

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


logger = logging.getLogger(__name__)


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

    DOC_STATUS_VALIDOS = {
        DOC_APROVADO,
        DOC_CORRIGIR,
        DOC_REPROVADO,
        DOC_EM_ANALISE,
        DOC_RASCUNHO,
    }

    # =========================================================
    # DOCUMENTOS OCR AUXILIARES — NÃO MOVEM FLUXO DO PROJETO
    # =========================================================

    TIPOS_OCR_ISOLADOS = {
        "OCR Dados Brutos",
        "OCR Documentos Pessoais",
        "OCR Ficha Cadastral SIG",
        "OCR Confrontantes Croqui",
        "OCR Matrícula",
    }

    @staticmethod
    def _documento_participa_fluxo(
        doc: DocumentoTecnico,
    ) -> bool:

        if not doc:
            return False

        return (
            doc.tipo
            not in ProjectFluxoService.TIPOS_OCR_ISOLADOS
        )

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

        documentos_fluxo: List[DocumentoTecnico] = [
            doc
            for doc in documentos
            if ProjectFluxoService._documento_participa_fluxo(doc)
        ]

        if not documentos_fluxo:
            logger.info(
                "Projeto possui apenas documentos OCR auxiliares. project_id=%s",
                project_id,
            )

            return ProjectFluxoService._definir_status(
                db=db,
                project_id=project_id,
                status=ProjectFluxoService.STATUS_DOCUMENTOS_EM_ANALISE,
                descricao="Projeto possui apenas documentos OCR auxiliares.",
                definido_por_usuario_id=definido_por_usuario_id,
            )

        total = len(documentos_fluxo)
        aprovados = 0
        corrigir = 0
        reprovados = 0
        em_analise = 0

        for doc in documentos_fluxo:

            status_doc = (
                (doc.status_tecnico or "")
                .upper()
                .strip()
            )

            if (
                status_doc
                not in ProjectFluxoService.DOC_STATUS_VALIDOS
            ):

                logger.warning(
                    "Status técnico inválido detectado. "
                    "documento_id=%s status=%s",
                    getattr(doc, "id", None),
                    status_doc,
                )

                em_analise += 1
                continue

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
    def reavaliar_fluxo_projeto(
        db: Session,
        project_id: int,
        definido_por_usuario_id: int | None = None,
    ) -> ProjectStatus:
        
        return ProjectFluxoService.avaliar_fluxo_projeto(
            db=db,
            project_id=project_id,
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

        ultimo_status: ProjectStatus | None = (
            db.query(ProjectStatus)
            .filter(ProjectStatus.project_id == project_id)
            .order_by(ProjectStatus.created_at.desc())
            .first()
        )

        if ultimo_status and ultimo_status.status == status:
            return ultimo_status

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