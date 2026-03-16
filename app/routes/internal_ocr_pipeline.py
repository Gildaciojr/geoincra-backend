from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.ocr_pipeline_service import OcrPipelineService

logger = logging.getLogger("geoincra.ocr_pipeline")

router = APIRouter(
    prefix="/internal/ocr",
    tags=["internal-ocr"],
)


# =========================================================
# PAYLOAD SCHEMA
# =========================================================

class OcrPipelineRequest(BaseModel):

    document_id: int
    categoria: str | None = None
    dados: Dict[str, Any]


class OcrPipelineResponse(BaseModel):

    success: bool
    document_id: int
    pipeline_executed: bool


# =========================================================
# OCR PIPELINE ENDPOINT
# =========================================================

@router.post(
    "/pipeline",
    response_model=OcrPipelineResponse,
    status_code=status.HTTP_200_OK,
)
def executar_pipeline_ocr(
    payload: OcrPipelineRequest,
    db: Session = Depends(get_db),
):
    """
    Endpoint interno chamado pelo worker após OCR.

    Fluxo:

    Worker OCR
        ↓
    POST /internal/ocr/pipeline
        ↓
    OcrPipelineService.executar_pipeline()
        ↓
    Matrícula
        ↓
    Geometria
        ↓
    Memorial
        ↓
    Croqui
        ↓
    CAD
        ↓
    SIGEF
    """

    try:

        logger.info(
            f"OCR pipeline iniciado para document_id={payload.document_id}"
        )

        result = OcrPipelineService.executar_pipeline(
            db=db,
            document_id=payload.document_id,
            prompt_categoria=payload.categoria,
            dados_extraidos=payload.dados,
        )

        logger.info(
            f"OCR pipeline finalizado document_id={payload.document_id}"
        )

        return OcrPipelineResponse(
            success=True,
            document_id=payload.document_id,
            pipeline_executed=bool(result),
        )

    except Exception as e:

        logger.exception(
            f"Erro no pipeline OCR document_id={payload.document_id}"
        )

        raise HTTPException(
            status_code=500,
            detail=f"Erro ao executar pipeline OCR: {str(e)}",
        )