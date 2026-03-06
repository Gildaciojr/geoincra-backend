from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.models.geometria import Geometria
from app.services.sigef_ods_service import SigefOdsService

router = APIRouter()


@router.post("/sigef/export/ods")
def export_sigef_ods(
    geometria_id: int,
    db: Session = Depends(get_db),
):

    geom = db.query(Geometria).get(geometria_id)

    if not geom:
        raise HTTPException(status_code=404, detail="Geometria não encontrada")

    ods, epsg_utm, metadata = SigefOdsService.gerar_ods_sigef(
        geojson=geom.geojson,
        epsg_origem=geom.epsg_origem,
    )

    path = SigefOdsService.salvar_ods_em_disco(
        imovel_id=geom.imovel_id,
        ods=ods,
    )

    return {
        "arquivo_path": path,
        "epsg_utm": epsg_utm,
        "metadata": metadata,
    }