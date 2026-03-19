from __future__ import annotations

import json
import os
from datetime import datetime

import geopandas as gpd
from shapely.geometry import shape, Polygon


class ShpExportService:

    # =========================================================
    # VALIDAÇÃO TOPOLOGICA (PESADA)
    # =========================================================
    @staticmethod
    def validar_geometria(geojson: str):
        geom = shape(json.loads(geojson))

        if geom.is_empty:
            raise ValueError("Geometria vazia")

        if not geom.is_valid:
            geom = geom.buffer(0)

        if geom.is_empty or not geom.is_valid:
            raise ValueError("Geometria inválida após correção topológica")

        if not isinstance(geom, Polygon):
            raise ValueError("Geometria deve ser POLYGON")

        return geom

    # =========================================================
    # GERAR SHP
    # =========================================================
    @staticmethod
    def gerar_shp(geojson: str):
        geom = ShpExportService.validar_geometria(geojson)

        gdf = gpd.GeoDataFrame(
            [{"id": 1}],
            geometry=[geom],
            crs="EPSG:4326",
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

        gdf.to_file(path)

        return folder  # retorna pasta completa (SHP = múltiplos arquivos)