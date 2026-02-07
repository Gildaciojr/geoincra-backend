from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.calculation import (
    CalculationBase,
    CalculationResult,
    ProposalRequest,
)
from app.services.calculation_service import CalculationService
from app.services.proposal_service import generate_full_proposal

router = APIRouter(prefix="/calculos", tags=["Cálculos"])


@router.post("/preview", response_model=CalculationResult)
def calcular_preview(
    payload: CalculationBase,
    db: Session = Depends(get_db),
):
    try:
        return CalculationService.calcular(db, payload)
    except Exception as e:
        raise HTTPException(400, str(e))


@router.post("/proposta")
def gerar_proposta(
    payload: ProposalRequest,
    db: Session = Depends(get_db),
):
    try:
        return generate_full_proposal(db, payload)
    except Exception as e:
        raise HTTPException(500, str(e))
