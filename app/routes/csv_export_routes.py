from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pathlib import Path

from app.core.deps import get_db
from app.models.geometria import Geometria
from app.services.csv_export_service import CsvExportService

router = APIRouter()


@router.post("/cad/export/csv/{geometria_id}")
def export_csv(
    geometria_id: int,
    db: Session = Depends(get_db),
):

    geom = db.query(Geometria).get(geometria_id)

    if not geom:
        raise HTTPException(status_code=404, detail="Geometria não encontrada")

    if not geom.geojson:
        raise HTTPException(status_code=400, detail="Geometria sem GeoJSON")

    csv = CsvExportService.gerar_csv(geom.geojson)

    path = CsvExportService.salvar_csv(
        imovel_id=geom.imovel_id,
        csv=csv,
    )

    file_path = Path(path)

    if not file_path.exists():
        raise HTTPException(status_code=500, detail="Erro ao gerar CSV")

    return FileResponse(
        path=file_path,
        filename=file_path.name,
        media_type="text/csv"
    )