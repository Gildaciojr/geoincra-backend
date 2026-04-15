from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path

from app.core.deps import get_db
from app.models.geometria import Geometria
from app.models.confrontante import Confrontante

from app.services.cad_export_service import CadExportService
from app.services.confrontante_output_adapter import ConfrontanteOutputAdapter

router = APIRouter()


@router.post("/cad/export/scr/{geometria_id}")
def export_cad_scr(
    geometria_id: int,
    db: Session = Depends(get_db),
):
    geom = db.query(Geometria).get(geometria_id)

    if not geom:
        raise HTTPException(status_code=404, detail="Geometria não encontrada")

    if not geom.geojson:
        raise HTTPException(status_code=400, detail="Geometria sem GeoJSON")

    # =========================================================
    # CONFRONTANTES DO BANCO (FONTE DA VERDADE)
    # =========================================================
    confrontantes_db = (
        db.query(Confrontante)
        .filter(Confrontante.geometria_id == geom.id)
        .order_by(
            Confrontante.ordem_segmento.asc().nullslast(),
            Confrontante.id.asc(),
        )
        .all()
    )

    confrontantes_formatados = ConfrontanteOutputAdapter.from_models(
        confrontantes_db
    )

    # =========================================================
    # GERAÇÃO DO SCR
    # =========================================================
    scr = CadExportService.gerar_scr(
        geojson=geom.geojson,
        confrontantes=confrontantes_formatados,
    )

    path = CadExportService.salvar_scr(
        imovel_id=geom.imovel_id,
        scr=scr,
    )

    file_path = Path(path)

    if not file_path.exists():
        raise HTTPException(status_code=500, detail="Erro ao gerar arquivo SCR")

    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="text/plain",
    )