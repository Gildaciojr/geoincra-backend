# app/services/sobreposicao_service.py

from shapely.geometry import shape
from fastapi import HTTPException
import json


class SobreposicaoService:

    @staticmethod
    def calcular(geojson_base: str, geojson_afetado: str):
        try:
            g1 = shape(json.loads(geojson_base))
            g2 = shape(json.loads(geojson_afetado))
        except Exception:
            raise HTTPException(
                status_code=400,
                detail="GeoJSON inválido para análise de sobreposição.",
            )

        if not g1.intersects(g2):
            return None

        intersecao = g1.intersection(g2)

        if intersecao.is_empty:
            return None

        area_base = g1.area
        area_intersecao = intersecao.area

        if area_base <= 0:
            return None

        percentual = (area_intersecao / area_base) * 100

        return {
            "area_intersecao": area_intersecao,
            "percentual": percentual,
        }
