from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.geometria import Geometria
from app.services.cad_export_service import CadExportService

router = APIRouter()


@router.post("/cad/export/scr")
def export_cad_scr(
    geometria_id: int,
    db: Session = Depends(get_db),
):

    geom = db.query(Geometria).get(geometria_id)

    if not geom:
        raise HTTPException(status_code=404, detail="Geometria não encontrada")

    scr = CadExportService.gerar_scr(geom.geojson)

    path = CadExportService.salvar_scr(
        imovel_id=geom.imovel_id,
        scr=scr,
    )

    return {
        "arquivo_path": path
    }