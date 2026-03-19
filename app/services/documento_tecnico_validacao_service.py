# app/services/documento_tecnico_validacao_service.py

from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from app.models.documento_tecnico import DocumentoTecnico
from app.models.documento_tecnico_checklist import DocumentoTecnicoChecklist


class DocumentoTecnicoValidacaoService:

    STATUS_APROVADO = "APROVADO"
    STATUS_CORRIGIR = "CORRIGIR"
    STATUS_REPROVADO = "REPROVADO"
    STATUS_EM_ANALISE = "EM_ANALISE"

    @staticmethod
    def validar_documento(
        db: Session,
        documento: DocumentoTecnico,
    ) -> DocumentoTecnico:

        checklist_itens: List[DocumentoTecnicoChecklist] = (
            db.query(DocumentoTecnicoChecklist)
            .filter(DocumentoTecnicoChecklist.documento_tecnico_id == documento.id)
            .all()
        )

        if not checklist_itens:
            return DocumentoTecnicoValidacaoService._atualizar_status(
                db,
                documento,
                DocumentoTecnicoValidacaoService.STATUS_CORRIGIR,
                "Checklist técnico não encontrado.",
            )

        pendentes_criticos = []
        pendentes_nao_criticos = []

        for item in checklist_itens:

            # ✔ OK passa
            if item.status == "OK":
                continue

            # ❗ ERRO obrigatório → reprova direto
            if item.status == "ERRO" and item.obrigatorio:
                pendentes_criticos.append(item)
                continue

            # ❗ NA obrigatório → reprova também
            if item.status == "NA" and item.obrigatorio:
                pendentes_criticos.append(item)
                continue

            # ⚠ ALERTA ou NA não obrigatório → corrigir
            pendentes_nao_criticos.append(item)

        if pendentes_criticos:
            return DocumentoTecnicoValidacaoService._atualizar_status(
                db,
                documento,
                DocumentoTecnicoValidacaoService.STATUS_REPROVADO,
                DocumentoTecnicoValidacaoService._montar_observacao(
                    "Itens obrigatórios pendentes",
                    pendentes_criticos,
                ),
            )

        if pendentes_nao_criticos:
            return DocumentoTecnicoValidacaoService._atualizar_status(
                db,
                documento,
                DocumentoTecnicoValidacaoService.STATUS_CORRIGIR,
                DocumentoTecnicoValidacaoService._montar_observacao(
                    "Itens não obrigatórios pendentes",
                    pendentes_nao_criticos,
                ),
            )

        return DocumentoTecnicoValidacaoService._atualizar_status(
            db,
            documento,
            DocumentoTecnicoValidacaoService.STATUS_APROVADO,
            "Documento técnico validado automaticamente.",
        )

    @staticmethod
    def _atualizar_status(db, documento, status, observacao):
        documento.status_tecnico = status
        documento.observacoes_tecnicas = observacao
        documento.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(documento)

        return documento

    @staticmethod
    def _montar_observacao(titulo, itens):
        linhas = [titulo + ":"]
        for item in itens:
            linhas.append(f"- {item.descricao}")
        return "\n".join(linhas)