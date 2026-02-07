from __future__ import annotations

from fastapi import HTTPException

from app.models.documento_tecnico import DocumentoTecnico


class DocumentoTecnicoGuardService:
    """
    Travas de consistência do CORE (sem APIs):
    - Documento APROVADO (versão atual) não pode ser alterado por UPDATE comum.
    - Alterações devem ocorrer criando NOVA VERSÃO.
    """

    STATUS_APROVADO = "APROVADO"

    @staticmethod
    def bloquear_update_se_aprovado(documento: DocumentoTecnico):
        if documento.is_versao_atual and documento.status_tecnico == DocumentoTecnicoGuardService.STATUS_APROVADO:
            raise HTTPException(
                status_code=409,
                detail="Documento APROVADO (versão atual) não pode ser alterado. Crie uma nova versão.",
            )
