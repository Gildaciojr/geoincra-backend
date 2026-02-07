# app/services/documento_tecnico_aprovacao_service.py

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.documento_tecnico import DocumentoTecnico
from app.models.documento_tecnico_checklist import DocumentoTecnicoChecklist
from app.models.timeline import TimelineEntry
from app.services.project_fluxo_service import ProjectFluxoService

# 🔥 Automação: status do projeto + pagamentos após mudanças em documentos
from app.services.project_status_automation_service import ProjectStatusAutomationService
from app.models.pagamento import Pagamento
from app.services.pagamento_automacao_service import PagamentoAutomacaoService


class DocumentoTecnicoAprovacaoService:
    """
    Serviço responsável por aprovar, reprovar ou solicitar correções
    em documentos técnicos, com rastreabilidade completa.
    """

    STATUS_APROVADO = "APROVADO"
    STATUS_CORRIGIR = "CORRIGIR"
    STATUS_REPROVADO = "REPROVADO"
    STATUS_EM_ANALISE = "EM_ANALISE"

    @staticmethod
    def aprovar_documento(
        db: Session,
        documento_id: int,
        aprovado_por_usuario_id: int,
        parecer_tecnico: Optional[str] = None,
    ) -> DocumentoTecnico:
        """
        Aprova tecnicamente um documento.
        """

        doc = (
            db.query(DocumentoTecnico)
            .filter(DocumentoTecnico.id == documento_id)
            .first()
        )
        if not doc:
            raise ValueError("Documento técnico não encontrado.")

        # Atualiza status do documento
        doc.status_tecnico = DocumentoTecnicoAprovacaoService.STATUS_APROVADO
        doc.observacoes_tecnicas = parecer_tecnico
        doc.updated_at = datetime.utcnow()

        # Marca checklist como aprovado
        db.query(DocumentoTecnicoChecklist).filter(
            DocumentoTecnicoChecklist.documento_tecnico_id == documento_id
        ).update(
            {
                "aprovado": True,
                "aprovado_por_usuario_id": aprovado_por_usuario_id,
                "aprovado_em": datetime.utcnow(),
            }
        )

        # Timeline
        timeline = TimelineEntry(
            project_id=doc.imovel.project_id,
            titulo="Documento técnico aprovado",
            descricao=f"{doc.tipo} aprovado tecnicamente.",
            status=doc.status_tecnico,
            created_at=datetime.utcnow(),
        )

        db.add(timeline)
        db.commit()
        db.refresh(doc)

        # Reavalia fluxo do projeto
        ProjectFluxoService.avaliar_fluxo_projeto(
            db=db,
            project_id=doc.imovel.project_id,
            definido_por_usuario_id=aprovado_por_usuario_id,
        )

        # =========================================================
        # 🔥 AUTOMAÇÕES PÓS-EVENTO (SaaS)
        # 1) Recalcula status automático do projeto
        # 2) Reavalia pagamentos (liberação automática)
        # =========================================================
        ProjectStatusAutomationService.avaliar_e_atualizar_status(
            db=db,
            project_id=doc.imovel.project_id,
        )

        pagamentos = (
            db.query(Pagamento)
            .filter(Pagamento.project_id == doc.imovel.project_id)
            .all()
        )
        for pagamento in pagamentos:
            PagamentoAutomacaoService.avaliar_liberacao_pagamento(db, pagamento)

        return doc

    @staticmethod
    def solicitar_correcao(
        db: Session,
        documento_id: int,
        solicitado_por_usuario_id: int,
        motivo: str,
    ) -> DocumentoTecnico:
        """
        Solicita correções técnicas em um documento.
        """

        doc = (
            db.query(DocumentoTecnico)
            .filter(DocumentoTecnico.id == documento_id)
            .first()
        )
        if not doc:
            raise ValueError("Documento técnico não encontrado.")

        doc.status_tecnico = DocumentoTecnicoAprovacaoService.STATUS_CORRIGIR
        doc.observacoes_tecnicas = motivo
        doc.updated_at = datetime.utcnow()

        # Checklist permanece não aprovado
        db.query(DocumentoTecnicoChecklist).filter(
            DocumentoTecnicoChecklist.documento_tecnico_id == documento_id
        ).update(
            {
                "aprovado": False,
                "aprovado_por_usuario_id": None,
                "aprovado_em": None,
            }
        )

        timeline = TimelineEntry(
            project_id=doc.imovel.project_id,
            titulo="Correção solicitada em documento técnico",
            descricao=f"{doc.tipo}: {motivo}",
            status=doc.status_tecnico,
            created_at=datetime.utcnow(),
        )

        db.add(timeline)
        db.commit()
        db.refresh(doc)

        ProjectFluxoService.avaliar_fluxo_projeto(
            db=db,
            project_id=doc.imovel.project_id,
            definido_por_usuario_id=solicitado_por_usuario_id,
        )

        # =========================================================
        # 🔥 AUTOMAÇÕES PÓS-EVENTO
        # =========================================================
        ProjectStatusAutomationService.avaliar_e_atualizar_status(
            db=db,
            project_id=doc.imovel.project_id,
        )

        pagamentos = (
            db.query(Pagamento)
            .filter(Pagamento.project_id == doc.imovel.project_id)
            .all()
        )
        for pagamento in pagamentos:
            PagamentoAutomacaoService.avaliar_liberacao_pagamento(db, pagamento)

        return doc

    @staticmethod
    def reprovar_documento(
        db: Session,
        documento_id: int,
        reprovado_por_usuario_id: int,
        motivo: str,
    ) -> DocumentoTecnico:
        """
        Reprova tecnicamente um documento.
        """

        doc = (
            db.query(DocumentoTecnico)
            .filter(DocumentoTecnico.id == documento_id)
            .first()
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
                "aprovado": False,
                "aprovado_por_usuario_id": None,
                "aprovado_em": None,
            }
        )

        timeline = TimelineEntry(
            project_id=doc.imovel.project_id,
            titulo="Documento técnico reprovado",
            descricao=f"{doc.tipo}: {motivo}",
            status=doc.status_tecnico,
            created_at=datetime.utcnow(),
        )

        db.add(timeline)
        db.commit()
        db.refresh(doc)

        ProjectFluxoService.avaliar_fluxo_projeto(
            db=db,
            project_id=doc.imovel.project_id,
            definido_por_usuario_id=reprovado_por_usuario_id,
        )

        # =========================================================
        # 🔥 AUTOMAÇÕES PÓS-EVENTO
        # =========================================================
        ProjectStatusAutomationService.avaliar_e_atualizar_status(
            db=db,
            project_id=doc.imovel.project_id,
        )

        pagamentos = (
            db.query(Pagamento)
            .filter(Pagamento.project_id == doc.imovel.project_id)
            .all()
        )
        for pagamento in pagamentos:
            PagamentoAutomacaoService.avaliar_liberacao_pagamento(db, pagamento)

        return doc
