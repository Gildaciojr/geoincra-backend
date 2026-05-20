from __future__ import annotations

from fastapi import HTTPException

from app.models.documento_tecnico import DocumentoTecnico


class DocumentoTecnicoGuardService:
    """
    Travas de consistência do CORE.

    Responsabilidades:
    - Bloquear alteração direta de documento aprovado
    - Garantir versionamento correto
    - Isolar documentos OCR automáticos
    - Proteger integridade do fluxo técnico

    NÃO:
    - Executa OCR
    - Executa validação
    - Cria versões
    """

    STATUS_APROVADO = "APROVADO"

    TIPOS_OCR_ISOLADOS = {
        "OCR Dados Brutos",
        "OCR Documentos Pessoais",
        "OCR Ficha Cadastral SIG",
        "OCR Confrontantes Croqui",
    }

    @staticmethod
    def bloquear_update_se_aprovado(
        documento: DocumentoTecnico,
    ) -> None:

        if not documento:
            raise HTTPException(
                status_code=404,
                detail="Documento técnico inválido.",
            )

        # =====================================================
        # OCRs ISOLADOS
        # =====================================================
        if documento.tipo in (
            DocumentoTecnicoGuardService
            .TIPOS_OCR_ISOLADOS
        ):
            return

        # =====================================================
        # DOCUMENTO APROVADO
        # =====================================================
        if (
            documento.is_versao_atual
            and documento.status_tecnico
            == DocumentoTecnicoGuardService
            .STATUS_APROVADO
        ):

            raise HTTPException(
                status_code=409,
                detail=(
                    "Documento APROVADO "
                    "(versão atual) não pode "
                    "ser alterado diretamente. "
                    "Crie uma nova versão."
                ),
            )