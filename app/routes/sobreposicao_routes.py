# app/routes/sobreposicao_routes.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.schemas.sobreposicao import SobreposicaoResponse
from app.crud.sobreposicao_crud import analisar_sobreposicao

router = APIRouter()


@router.post(
    "/sobreposicao/{base_id}/{afetada_id}",
    response_model=SobreposicaoResponse,
)
def analisar(
    base_id: int,
    afetada_id: int,
    tipo: str,
    db: Session = Depends(get_db),
):
    result = analisar_sobreposicao(
        db=db,
        geometria_base_id=base_id,
        geometria_afetada_id=afetada_id,
        tipo=tipo,
    )

    if not result:
        raise HTTPException(
            status_code=404,
            detail="Nenhuma sobreposição detectada.",
        )

    return result
