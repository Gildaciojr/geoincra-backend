from __future__ import annotations

import json
import os
from datetime import datetime

import geopandas as gpd

from shapely.geometry import Polygon
from app.services.geometria_service import GeometriaService


class ShpExportService:

    # =========================================================
    # VALIDAÇÃO TOPOLOGICA (ROBUSTA)
    # =========================================================
    @staticmethod
    def validar_geometria(geojson: str) -> Polygon:
        try:
            return GeometriaService._parse_polygon_geojson(geojson)
        except Exception as exc:
            raise ValueError("Geometria inválida para SHP") from exc

    # =========================================================
    # GERAR SHP PROFISSIONAL
    # =========================================================
    @staticmethod
    def gerar_shp(
        geojson: str,
        epsg: int = 4326,
    ):
        geom = ShpExportService.validar_geometria(geojson)

        area = geom.area
        perimetro = geom.length

        gdf = gpd.GeoDataFrame(
            [
                {
                    "id": 1,
                    "area_m2": round(area, 4),
                    "perimetro_m": round(perimetro, 4),
                    "data_geracao": datetime.utcnow().isoformat(),
                }
            ],
            geometry=[geom],
            crs=f"EPSG:{epsg}",
        )

        return gdf

    # =========================================================
    # SALVAR SHP
    # =========================================================
    @staticmethod
    def salvar_shp(
        imovel_id: int,
        gdf,
        base_dir: str = "app/uploads/imoveis",
    ) -> str:

        ts = int(datetime.utcnow().timestamp())

        folder = os.path.join(base_dir, str(imovel_id), "shp", str(ts))
        os.makedirs(folder, exist_ok=True)

        path = os.path.join(folder, "area.shp")

        # salvar com encoding e schema correto
        gdf.to_file(
            path,
            driver="ESRI Shapefile",
            encoding="utf-8",
        )

        return folder