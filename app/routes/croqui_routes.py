# app/routes/croqui_routes.py

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.geometria import Geometria
from app.services.croqui_service import CroquiService

router = APIRouter()


@router.get("/croqui/{geometria_id}")
def gerar_croqui_svg(geometria_id: int, db: Session = Depends(get_db)):
    geom = db.query(Geometria).get(geometria_id)
    if not geom:
        raise HTTPException(status_code=404, detail="Geometria não encontrada.")

    if not geom.geojson:
        raise HTTPException(status_code=400, detail="Geometria sem GeoJSON.")

    svg = CroquiService.gerar_svg(geom.geojson)
    return Response(content=svg, media_type="image/svg+xml")
