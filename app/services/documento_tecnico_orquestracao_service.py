# app/services/documento_tecnico_orquestracao_service.py

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.documento_tecnico import DocumentoTecnico
from app.services.documento_tecnico_validacao_service import (
    DocumentoTecnicoValidacaoService,
)
from app.services.project_fluxo_service import ProjectFluxoService
from app.models.imovel import Imovel


class DocumentoTecnicoOrquestracaoService:
    """
    Orquestra ações automáticas após eventos em Documento Técnico.

    Responsabilidades:
    - Executar validação técnica automática
    - Atualizar status do projeto conforme regras do fluxo
    - Manter isolamento entre CRUD, validação e fluxo

    NÃO:
    - Cria versões
    - Integra APIs externas
    - Executa OCR
    """

    @staticmethod
    def processar_evento_documento_tecnico(
        db: Session,
        documento: DocumentoTecnico,
    ) -> DocumentoTecnico:
        """
        Executa o pipeline completo após criação/atualização/versionamento
        de um Documento Técnico.
        """

        # =========================================================
        # 1️⃣ Validação técnica automática
        # =========================================================
        documento = DocumentoTecnicoValidacaoService.validar_documento(
            db=db,
            documento=documento,
        )

        # =========================================================
        # 2️⃣ Atualização do fluxo do projeto
        # =========================================================
        imovel = (
            db.query(Imovel)
            .filter(Imovel.id == documento.imovel_id)
            .first()
        )

        if imovel:
            ProjectFluxoService.reavaliar_fluxo_projeto(
                db=db,
                project_id=imovel.project_id,
            )

        return documento
