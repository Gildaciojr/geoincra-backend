# app/routes/croqui_routes.py

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.geometria import Geometria
from app.models.confrontante import Confrontante

from app.services.croqui_service import CroquiService
from app.services.confrontante_output_adapter import ConfrontanteOutputAdapter

router = APIRouter()


@router.get("/croqui/{geometria_id}")
def gerar_croqui_svg(geometria_id: int, db: Session = Depends(get_db)):
    geom = db.query(Geometria).get(geometria_id)

    if not geom:
        raise HTTPException(status_code=404, detail="Geometria não encontrada.")

    if not geom.geojson:
        raise HTTPException(status_code=400, detail="Geometria sem GeoJSON.")

    # =========================================================
    # 🔥 BUSCAR CONFRONTANTES DO BANCO (FONTE DA VERDADE)
    # =========================================================
    confrontantes_db = (
        db.query(Confrontante)
        .filter(Confrontante.geometria_id == geom.id)
        .all()
    )

    # =========================================================
    # 🔥 ADAPTAR PARA FORMATO DO CROQUI
    # =========================================================
    confrontantes_formatados = ConfrontanteOutputAdapter.from_models(confrontantes_db)

    # =========================================================
    # 🔥 GERAR SVG COM DADOS CORRETOS
    # =========================================================
    svg = CroquiService.gerar_svg(
        geom.geojson,
        confrontantes=confrontantes_formatados
    )

    return Response(content=svg, media_type="image/svg+xml")