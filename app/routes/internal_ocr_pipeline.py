from __future__ import annotations

import logging
from typing import Any, Dict, Optional

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


class OcrPipelineRequest(BaseModel):
    document_id: int
    ocr_result_id: Optional[int] = None
    categoria: str | None = None
    dados: Dict[str, Any]


class OcrPipelineResponse(BaseModel):
    success: bool
    document_id: int
    ocr_result_id: Optional[int] = None
    pipeline_executed: bool
    pipeline_details: Dict[str, Any]


@router.post(
    "/pipeline",
    response_model=OcrPipelineResponse,
    status_code=status.HTTP_200_OK,
)
def executar_pipeline_ocr(
    payload: OcrPipelineRequest,
    db: Session = Depends(get_db),
):
    try:
        logger.info(
            "OCR pipeline iniciado para document_id=%s ocr_result_id=%s",
            payload.document_id,
            payload.ocr_result_id,
        )

        result = OcrPipelineService.executar_pipeline(
            db=db,
            document_id=payload.document_id,
            ocr_result_id=payload.ocr_result_id,
            prompt_categoria=payload.categoria,
            dados_extraidos=payload.dados,
        )

        logger.info(
            "OCR pipeline finalizado para document_id=%s ocr_result_id=%s success=%s",
            payload.document_id,
            payload.ocr_result_id,
            bool(result.get("success")),
        )

        return OcrPipelineResponse(
            success=bool(result.get("success")),
            document_id=payload.document_id,
            ocr_result_id=payload.ocr_result_id,
            pipeline_executed=True,
            pipeline_details=result,
        )

    except Exception as e:
        logger.exception(
            "Erro no pipeline OCR document_id=%s ocr_result_id=%s",
            payload.document_id,
            payload.ocr_result_id,
        )

        raise HTTPException(
            status_code=500,
            detail=f"Erro ao executar pipeline OCR: {str(e)}",
        )