from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user_required
from app.schemas.calculation import CalculationBase
from app.services.calculation_service import CalculationService
from app.services.pdf_service import gerar_pdf_orcamento

router = APIRouter(prefix="/orcamentos", tags=["Orçamentos"])


@router.post("/preview")
def gerar_orcamento(
    payload: CalculationBase,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_user_required),
):
    try:
        resultado = CalculationService.calcular(db, payload)

        pdf_path = gerar_pdf_orcamento(
            project_id=None,
            calculation=resultado,
        )

        return {
            "valor_base": resultado.valor_base,
            "extras": resultado.valor_variaveis_fixas + resultado.valor_variaveis_percentuais,
            "valor_art": resultado.valor_art,
            "valor_cartorio": resultado.valor_cartorio,
            "total": resultado.total_final,
            "pdf_orcamento_path": pdf_path,
        }

    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
