# app/services/documento_tecnico_validacao_service.py

from __future__ import annotations

from datetime import datetime
from typing import List

from sqlalchemy.orm import Session

from app.models.documento_tecnico import DocumentoTecnico
from app.models.documento_tecnico_checklist import DocumentoTecnicoChecklist
from app.schemas.documento_tecnico import DocumentoTecnicoUpdate


class DocumentoTecnicoValidacaoService:
    """
    Serviço responsável por validar tecnicamente um Documento Técnico
    com base no checklist associado e em regras técnicas do sistema.

    NÃO executa OCR
    NÃO integra APIs externas
    NÃO altera versionamento

    Atua apenas sobre:
    - status_tecnico
    - observacoes_tecnicas
    """

    STATUS_APROVADO = "APROVADO"
    STATUS_CORRIGIR = "CORRIGIR"
    STATUS_REPROVADO = "REPROVADO"
    STATUS_EM_ANALISE = "EM_ANALISE"

    @staticmethod
    def validar_documento(
        db: Session,
        documento: DocumentoTecnico,
    ) -> DocumentoTecnico:
        """
        Executa validação completa do documento técnico.

        Retorna o próprio documento já atualizado.
        """

        checklist_itens: List[DocumentoTecnicoChecklist] = (
            db.query(DocumentoTecnicoChecklist)
            .filter(
                DocumentoTecnicoChecklist.documento_tecnico_id == documento.id
            )
            .all()
        )

        if not checklist_itens:
            
            return DocumentoTecnicoValidacaoService._atualizar_status(
                db=db,
                documento=documento,
                status=DocumentoTecnicoValidacaoService.STATUS_CORRIGIR,
                observacao="Checklist técnico não encontrado.",
            )

        # =========================================================
        # ANÁLISE DOS ITENS DO CHECKLIST
        # =========================================================

        pendentes_criticos = []
        pendentes_nao_criticos = []

        for item in checklist_itens:
            if item.atendido is True:
                continue

            if item.critico:
                pendentes_criticos.append(item)
            else:
                pendentes_nao_criticos.append(item)

        # =========================================================
        # REGRAS DE DECISÃO
        # =========================================================

        if pendentes_criticos:
            observacao = DocumentoTecnicoValidacaoService._montar_observacao(
                titulo="Itens críticos pendentes",
                itens=pendentes_criticos,
            )
            return DocumentoTecnicoValidacaoService._atualizar_status(
                db=db,
                documento=documento,
                status=DocumentoTecnicoValidacaoService.STATUS_REPROVADO,
                observacao=observacao,
            )

        if pendentes_nao_criticos:
            observacao = DocumentoTecnicoValidacaoService._montar_observacao(
                titulo="Itens pendentes para correção",
                itens=pendentes_nao_criticos,
            )
            return DocumentoTecnicoValidacaoService._atualizar_status(
                db=db,
                documento=documento,
                status=DocumentoTecnicoValidacaoService.STATUS_CORRIGIR,
                observacao=observacao,
            )

        # =========================================================
        # DOCUMENTO APROVADO
        # =========================================================

        return DocumentoTecnicoValidacaoService._atualizar_status(
            db=db,
            documento=documento,
            status=DocumentoTecnicoValidacaoService.STATUS_APROVADO,
            observacao="Documento técnico validado automaticamente com sucesso.",
        )

    # =========================================================
    # MÉTODOS AUXILIARES
    # =========================================================

    @staticmethod
    def _atualizar_status(
        db: Session,
        documento: DocumentoTecnico,
        status: str,
        observacao: str,
    ) -> DocumentoTecnico:
        """
        Atualiza status técnico e observações do documento.
        """

        documento.status_tecnico = status
        documento.observacoes_tecnicas = observacao
        documento.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(documento)

        return documento

    @staticmethod
    def _montar_observacao(
        titulo: str,
        itens: List[DocumentoTecnicoChecklist],
    ) -> str:
        """
        Monta observação técnica padronizada a partir de itens pendentes.
        """

        linhas = [titulo + ":"]
        for item in itens:
            linhas.append(f"- {item.descricao}")

        return "\n".join(linhas)
