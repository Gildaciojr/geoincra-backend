# app/services/documento_tecnico_aprovacao_service.py
from __future__ import annotations

import logging

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.documento_tecnico import DocumentoTecnico
from app.models.documento_tecnico_checklist import DocumentoTecnicoChecklist
from app.models.timeline import TimelineEntry
from app.services.project_fluxo_service import ProjectFluxoService

from app.services.project_status_automation_service import ProjectStatusAutomationService
from app.models.pagamento import Pagamento
from app.services.pagamento_automacao_service import PagamentoAutomacaoService

logger = logging.getLogger(__name__)


class DocumentoTecnicoAprovacaoService:

    STATUS_APROVADO = "APROVADO"
    STATUS_CORRIGIR = "CORRIGIR"
    STATUS_REPROVADO = "REPROVADO"
    STATUS_EM_ANALISE = "EM_ANALISE"

    STATUS_CHECKLIST_OK = "OK"
    STATUS_CHECKLIST_ALERTA = "ALERTA"
    STATUS_CHECKLIST_ERRO = "ERRO"

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
            not in DocumentoTecnicoAprovacaoService
            .TIPOS_OCR_ISOLADOS
        )

    @staticmethod
    def aprovar_documento(
        db: Session,
        documento_id: int,
        aprovado_por_usuario_id: int,
        parecer_tecnico: Optional[str] = None,
    ) -> DocumentoTecnico:

        doc = db.get(
            DocumentoTecnico,
            documento_id,
        )

        if not doc:
            raise ValueError("Documento técnico não encontrado.")

        doc.status_tecnico = DocumentoTecnicoAprovacaoService.STATUS_APROVADO
        doc.observacoes_tecnicas = parecer_tecnico
        doc.updated_at = datetime.utcnow()

        # ✅ CORREÇÃO REAL
        db.query(DocumentoTecnicoChecklist).filter(
            DocumentoTecnicoChecklist.documento_tecnico_id == documento_id
        ).update(
            {
                "status": DocumentoTecnicoAprovacaoService.STATUS_CHECKLIST_OK,
                "validado_automaticamente": False,
                "validado_por_usuario_id": aprovado_por_usuario_id,
                "validado_em": datetime.utcnow(),
            }
        )

        timeline = TimelineEntry(
            project_id=doc.imovel.project_id,
            titulo="Documento técnico aprovado",
            descricao=f"{doc.tipo} aprovado tecnicamente.",
            status=doc.status_tecnico,
            created_at=datetime.utcnow(),
        )

        try:

            db.add(timeline)

            db.commit()

            db.refresh(doc)

        except SQLAlchemyError:

            db.rollback()

            raise



        if (
            DocumentoTecnicoAprovacaoService
            ._documento_participa_fluxo(doc)
        ):

            try:

                ProjectFluxoService.avaliar_fluxo_projeto(
                    db=db,
                    project_id=doc.imovel.project_id,
                    definido_por_usuario_id=(
                        aprovado_por_usuario_id
                    ),
                )

            except Exception:

                logger.exception(
                    "Falha ao avaliar fluxo "
                    "do projeto."
                )

            try:

                ProjectStatusAutomationService.avaliar_e_atualizar_status(
                    db=db,
                    project_id=doc.imovel.project_id,
                )

            except Exception:

                logger.exception(
                    "Falha ao atualizar status "
                    "automático do projeto."
                )

            try:

                pagamentos = db.query(Pagamento).filter(
                    Pagamento.project_id
                    == doc.imovel.project_id
                ).all()

                for pagamento in pagamentos:

                    PagamentoAutomacaoService.avaliar_liberacao_pagamento(
                        db,
                        pagamento,
                    )

            except Exception:

                logger.exception(
                    "Falha ao avaliar automações "
                    "de pagamento."
                )

        else:

            logger.info(
                "Documento OCR isolado ignorado "
                "nas automações de fluxo."
            )

        return doc

    @staticmethod
    def solicitar_correcao(
        db: Session,
        documento_id: int,
        solicitado_por_usuario_id: int,
        motivo: str,
    ) -> DocumentoTecnico:

        doc = db.get(
            DocumentoTecnico,
            documento_id,
        )

        if not doc:
            raise ValueError("Documento técnico não encontrado.")

        doc.status_tecnico = DocumentoTecnicoAprovacaoService.STATUS_CORRIGIR
        doc.observacoes_tecnicas = motivo
        doc.updated_at = datetime.utcnow()

        db.query(DocumentoTecnicoChecklist).filter(
            DocumentoTecnicoChecklist.documento_tecnico_id == documento_id
        ).update(
            {
                "status": DocumentoTecnicoAprovacaoService.STATUS_CHECKLIST_ALERTA,
                "validado_automaticamente": False,
                "validado_por_usuario_id": None,
                "validado_em": None,
            }
        )

        timeline = TimelineEntry(
            project_id=doc.imovel.project_id,
            titulo="Correção solicitada em documento técnico",
            descricao=f"{doc.tipo}: {motivo}",
            status=doc.status_tecnico,
            created_at=datetime.utcnow(),
        )

        try:

            db.add(timeline)

            db.commit()

            db.refresh(doc)

        except SQLAlchemyError:

            db.rollback()

            raise

        if (
            DocumentoTecnicoAprovacaoService
            ._documento_participa_fluxo(doc)
        ):

            try:

                ProjectFluxoService.avaliar_fluxo_projeto(
                    db=db,
                    project_id=doc.imovel.project_id,
                    definido_por_usuario_id=(
                        solicitado_por_usuario_id
                    ),
                )

            except Exception:

                logger.exception(
                    "Falha ao avaliar fluxo "
                    "do projeto."
                )

            try:

                ProjectStatusAutomationService.avaliar_e_atualizar_status(
                    db=db,
                    project_id=doc.imovel.project_id,
                )

            except Exception:

                logger.exception(
                    "Falha ao atualizar status "
                    "automático do projeto."
                )

            try:

                pagamentos = db.query(Pagamento).filter(
                    Pagamento.project_id
                    == doc.imovel.project_id
                ).all()

                for pagamento in pagamentos:

                    PagamentoAutomacaoService.avaliar_liberacao_pagamento(
                        db,
                        pagamento,
                    )

            except Exception:

                logger.exception(
                    "Falha ao avaliar automações "
                    "de pagamento."
                )

        else:

            logger.info(
                "Documento OCR isolado ignorado "
                "nas automações de fluxo."
            )

        return doc

    @staticmethod
    def reprovar_documento(
        db: Session,
        documento_id: int,
        reprovado_por_usuario_id: int,
        motivo: str,
    ) -> DocumentoTecnico:

        doc = db.get(
            DocumentoTecnico,
            documento_id,
        )

        if not doc:
            raise ValueError("Documento técnico não encontrado.")

        doc.status_tecnico = DocumentoTecnicoAprovacaoService.STATUS_REPROVADO
        doc.observacoes_tecnicas = motivo
        doc.updated_at = datetime.utcnow()

        db.query(DocumentoTecnicoChecklist).filter(
            DocumentoTecnicoChecklist.documento_tecnico_id == documento_id
        ).update(
            {
                "status": DocumentoTecnicoAprovacaoService.STATUS_CHECKLIST_ERRO,
                "validado_automaticamente": False,
                "validado_por_usuario_id": None,
                "validado_em": None,
            }
        )

        timeline = TimelineEntry(
            project_id=doc.imovel.project_id,
            titulo="Documento técnico reprovado",
            descricao=f"{doc.tipo}: {motivo}",
            status=doc.status_tecnico,
            created_at=datetime.utcnow(),
        )

        try:

            db.add(timeline)

            db.commit()

            db.refresh(doc)

        except SQLAlchemyError:

            db.rollback()

            raise

        if (
            DocumentoTecnicoAprovacaoService
            ._documento_participa_fluxo(doc)
        ):

            try:

                ProjectFluxoService.avaliar_fluxo_projeto(
                    db=db,
                    project_id=doc.imovel.project_id,
                    definido_por_usuario_id=(
                        reprovado_por_usuario_id
                    ),
                )

            except Exception:

                logger.exception(
                    "Falha ao avaliar fluxo "
                    "do projeto."
                )

            try:

                ProjectStatusAutomationService.avaliar_e_atualizar_status(
                    db=db,
                    project_id=doc.imovel.project_id,
                )

            except Exception:

                logger.exception(
                    "Falha ao atualizar status "
                    "automático do projeto."
                )

            try:

                pagamentos = db.query(Pagamento).filter(
                    Pagamento.project_id
                    == doc.imovel.project_id
                ).all()

                for pagamento in pagamentos:

                    PagamentoAutomacaoService.avaliar_liberacao_pagamento(
                        db,
                        pagamento,
                    )

            except Exception:

                logger.exception(
                    "Falha ao avaliar automações "
                    "de pagamento."
                )

        else:

            logger.info(
                "Documento OCR isolado ignorado "
                "nas automações de fluxo."
            )

        return doc