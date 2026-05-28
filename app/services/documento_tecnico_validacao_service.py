# app/services/documento_tecnico_validacao_service.py

from __future__ import annotations

import logging

from datetime import datetime
from typing import List

from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

from app.models.documento_tecnico import DocumentoTecnico
from app.models.documento_tecnico_checklist import (
    DocumentoTecnicoChecklist,
)


logger = logging.getLogger(__name__)


class DocumentoTecnicoValidacaoService:

    STATUS_APROVADO = "APROVADO"
    STATUS_CORRIGIR = "CORRIGIR"
    STATUS_REPROVADO = "REPROVADO"
    STATUS_EM_ANALISE = "EM_ANALISE"

    TIPOS_OCR_ISOLADOS = {
        "OCR Dados Brutos",
        "OCR Documentos Pessoais",
        "OCR Ficha Cadastral SIG",
        "OCR Confrontantes Croqui",
    }

    @staticmethod
    def validar_documento(
        db: Session,
        documento: DocumentoTecnico,
    ) -> DocumentoTecnico:

        if not documento:
            raise ValueError(
                "Documento técnico inválido."
            )

        # =====================================================
        # OCRs ISOLADOS NÃO ENTRAM EM CHECKLIST TÉCNICO
        # =====================================================
        if documento.tipo in (
            DocumentoTecnicoValidacaoService
            .TIPOS_OCR_ISOLADOS
        ):

            logger.info(
                "Documento OCR isolado ignorado "
                "na validação técnica. "
                "documento_id=%s tipo=%s",
                getattr(documento, "id", None),
                documento.tipo,
            )

            return DocumentoTecnicoValidacaoService._atualizar_status(
                db=db,
                documento=documento,
                status=(
                    DocumentoTecnicoValidacaoService
                    .STATUS_APROVADO
                ),
                observacao=(
                    "Documento OCR isolado validado "
                    "automaticamente."
                ),
            )

        # =====================================================
        # CHECKLIST TÉCNICO
        # =====================================================
        checklist_itens: List[
            DocumentoTecnicoChecklist
        ] = (
            db.query(DocumentoTecnicoChecklist)
            .filter(
                DocumentoTecnicoChecklist
                .documento_tecnico_id
                == documento.id
            )
            .all()
        )

        # =====================================================
        # DOCUMENTOS TÉCNICOS SEM CHECKLIST
        # =====================================================
        if not checklist_itens:

            logger.warning(
                "Checklist técnico não encontrado. "
                "documento_id=%s tipo=%s",
                getattr(documento, "id", None),
                getattr(documento, "tipo", None),
            )

            return DocumentoTecnicoValidacaoService._atualizar_status(
                db=db,
                documento=documento,
                status=(
                    DocumentoTecnicoValidacaoService
                    .STATUS_CORRIGIR
                ),
                observacao=(
                    "Checklist técnico não encontrado."
                ),
            )

        pendentes_criticos: List[
            DocumentoTecnicoChecklist
        ] = []

        pendentes_nao_criticos: List[
            DocumentoTecnicoChecklist
        ] = []

        # =====================================================
        # PROCESSAMENTO DOS ITENS
        # =====================================================
        for item in checklist_itens:

            status_item = (
                str(item.status or "")
                .strip()
                .upper()
            )

            # =================================================
            # ITEM OK
            # =================================================
            if status_item == (
                DocumentoTecnicoValidacaoService
                .CHECKLIST_OK
            ):
                continue

            # =================================================
            # ERRO OBRIGATÓRIO
            # =================================================
            if (
                status_item == "ERRO"
                and item.obrigatorio
            ):

                pendentes_criticos.append(item)

                continue

            # =================================================
            # NÃO APLICÁVEL OBRIGATÓRIO
            # =================================================
            if (
                status_item
                == DocumentoTecnicoValidacaoService.CHECKLIST_NA
            ):
                pendentes_nao_criticos.append(item)
                continue

            # =================================================
            # ALERTAS / NÃO OBRIGATÓRIOS
            # =================================================
            pendentes_nao_criticos.append(item)

        # =====================================================
        # REPROVAÇÃO
        # =====================================================
        if pendentes_criticos:

            logger.warning(
                "Documento técnico reprovado. "
                "documento_id=%s pendencias=%s",
                getattr(documento, "id", None),
                len(pendentes_criticos),
            )

            return DocumentoTecnicoValidacaoService._atualizar_status(
                db=db,
                documento=documento,
                status=(
                    DocumentoTecnicoValidacaoService
                    .STATUS_REPROVADO
                ),
                observacao=(
                    DocumentoTecnicoValidacaoService
                    ._montar_observacao(
                        "Itens obrigatórios pendentes",
                        pendentes_criticos,
                    )
                ),
            )

        # =====================================================
        # CORRIGIR
        # =====================================================
        if pendentes_nao_criticos:

            logger.info(
                "Documento técnico exige correção. "
                "documento_id=%s pendencias=%s",
                getattr(documento, "id", None),
                len(pendentes_nao_criticos),
            )

            return DocumentoTecnicoValidacaoService._atualizar_status(
                db=db,
                documento=documento,
                status=(
                    DocumentoTecnicoValidacaoService
                    .STATUS_CORRIGIR
                ),
                observacao=(
                    DocumentoTecnicoValidacaoService
                    ._montar_observacao(
                        "Itens não obrigatórios pendentes",
                        pendentes_nao_criticos,
                    )
                ),
            )

        # =====================================================
        # APROVAÇÃO
        # =====================================================
        logger.info(
            "Documento técnico aprovado automaticamente. "
            "documento_id=%s",
            getattr(documento, "id", None),
        )

        return DocumentoTecnicoValidacaoService._atualizar_status(
            db=db,
            documento=documento,
            status=(
                DocumentoTecnicoValidacaoService
                .STATUS_APROVADO
            ),
            observacao=(
                "Documento técnico validado automaticamente."
            ),
        )

    @staticmethod
    def _atualizar_status(
        db: Session,
        documento: DocumentoTecnico,
        status: str,
        observacao: str,
    ) -> DocumentoTecnico:

        documento.status_tecnico = status

        documento.observacoes_tecnicas = observacao

        documento.updated_at = datetime.utcnow()

        try:
            db.commit()

            db.refresh(documento)

            return documento
        
        except SQLAlchemyError:

            db.rollback()

            raise

    @staticmethod
    def _montar_observacao(
        titulo: str,
        itens: List[DocumentoTecnicoChecklist],
    ) -> str:

        linhas = [f"{titulo}:"]

        for item in itens:

            descricao = (
                item.descricao
                if item.descricao
                else "Item técnico sem descrição"
            )

            linhas.append(
                f"- {descricao}"
            )

        return "\n".join(linhas)