from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import json

from app.core.deps import get_db
from app.models.imovel import Imovel
from app.models.geometria import Geometria

router = APIRouter()


@router.get("/map/config")
def map_config():
    from app.services.map_service import get_mapbox_config

    config = get_mapbox_config()
    return {
        "enabled": bool(config),
        "config": config,
    }


@router.get("/imoveis/{imovel_id}/map")
def get_imovel_map(imovel_id: int, db: Session = Depends(get_db)):
    """
    Retorna todas as geometrias do imóvel no formato GeoJSON FeatureCollection.
    Endpoint oficial para renderização de mapas (Mapbox / Leaflet / SIGEF).
    """

    imovel = db.query(Imovel).filter(Imovel.id == imovel_id).first()
    if not imovel:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado.")

    geometrias = (
        db.query(Geometria)
        .filter(Geometria.imovel_id == imovel_id)
        .order_by(Geometria.created_at.asc())
        .all()
    )

    features = []

    for geom in geometrias:
        try:
            geometry = json.loads(geom.geojson)
        except Exception:
            # GeoJSON inválido não deve quebrar o mapa inteiro
            continue

        features.append(
            {
                "type": "Feature",
                "id": geom.id,
                "geometry": geometry,
                "properties": {
                    "geometria_id": geom.id,
                    "imovel_id": geom.imovel_id,
                    "nome": geom.nome,
                    "area_hectares": geom.area_hectares,
                    "perimetro_m": geom.perimetro_m,
                    "epsg_origem": geom.epsg_origem,
                    "epsg_utm": geom.epsg_utm,
                    "created_at": geom.created_at.isoformat(),
                    "updated_at": geom.updated_at.isoformat(),
                },
            }
        )

    return {
        "type": "FeatureCollection",
        "features": features,
    }
