# app/services/documento_tecnico_orquestracao_service.py

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.documento_tecnico import DocumentoTecnico
from app.models.imovel import Imovel
from app.services.documento_tecnico_validacao_service import (
    DocumentoTecnicoValidacaoService,
)
from app.services.project_fluxo_service import ProjectFluxoService


logger = logging.getLogger(__name__)


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

        if not documento:
            raise ValueError(
                "Documento técnico inválido."
            )

        tipos_sem_fluxo = {
            "OCR Dados Brutos",
            "OCR Documentos Pessoais",
            "OCR Ficha Cadastral SIG",
            "OCR Confrontantes Croqui",
        }

        if documento.tipo in tipos_sem_fluxo:

            logger.info(
                "Documento técnico OCR isolado não participa "
                "do fluxo do projeto. documento_id=%s tipo=%s",
                getattr(documento, "id", None),
                documento.tipo,
            )

            return documento

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

            try:

                ProjectFluxoService.reavaliar_fluxo_projeto(
                    db=db,
                    project_id=imovel.project_id,
                )

            except Exception:

                logger.exception(
                    "Falha ao reavaliar fluxo do projeto "
                    "após documento técnico. documento_id=%s imovel_id=%s",
                    getattr(documento, "id", None),
                    getattr(documento, "imovel_id", None),
                )

        return documento