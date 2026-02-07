# app/routes/memorial_routes.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.geometria import Geometria
from app.schemas.memorial import MemorialResponse
from app.services.memorial_service import MemorialService

router = APIRouter()


@router.get(
    "/memorial/{geometria_id}",
    response_model=MemorialResponse,
)
def gerar_memorial(geometria_id: int, db: Session = Depends(get_db)):
    geom = db.query(Geometria).get(geometria_id)
    if not geom:
        raise HTTPException(status_code=404, detail="Geometria não encontrada.")

    if not geom.geojson:
        raise HTTPException(status_code=400, detail="Geometria sem GeoJSON.")

    if geom.area_hectares is None or geom.perimetro_m is None:
        raise HTTPException(
            status_code=400,
            detail="Geometria sem área/perímetro calculados (execute cálculo primeiro).",
        )

    payload = MemorialService.gerar_memorial(
        geometria_id=geom.id,
        geojson=geom.geojson,
        area_hectares=float(geom.area_hectares),
        perimetro_m=float(geom.perimetro_m),
        prefixo_vertice="V",
    )

    return payload
