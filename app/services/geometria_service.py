from __future__ import annotations

import json
import math
from math import floor
from typing import Tuple

from fastapi import HTTPException
from pyproj import CRS, Transformer
from shapely.geometry import shape, Polygon


class GeometriaService:
    @staticmethod
    def _utm_epsg_from_lonlat(lon: float, lat: float) -> int:
        zona = int(floor((lon + 180.0) / 6.0) + 1)
        return (32600 + zona) if lat >= 0 else (32700 + zona)

    @staticmethod
    def _parse_polygon_geojson(geojson: str) -> Polygon:
        try:
            obj = json.loads(geojson)
            geom = shape(obj)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="GeoJSON inválido.") from exc

        if not isinstance(geom, Polygon):
            raise HTTPException(status_code=400, detail="Geometria deve ser POLYGON.")

        if geom.is_empty:
            raise HTTPException(status_code=400, detail="Geometria vazia.")

        if not geom.is_valid:
            # 🔥 tentativa automática de correção topológica
            geom = geom.buffer(0)

        if geom.is_empty or not geom.is_valid:
            raise HTTPException(status_code=400, detail="Geometria inválida após correção.")

        return geom

    @staticmethod
    def _safe_float(value: float) -> float:
        try:
            v = float(value)
            if math.isnan(v) or math.isinf(v):
                return 0.0
            return v
        except Exception:
            return 0.0

    @staticmethod
    def calcular_area_perimetro(
        geojson: str,
        epsg_origem: int = 4326,
    ) -> Tuple[int, float, float]:

        geom = GeometriaService._parse_polygon_geojson(geojson)

        centroid = geom.centroid

        lon = float(centroid.x)
        lat = float(centroid.y)

        if math.isnan(lon) or math.isnan(lat):
            raise HTTPException(status_code=400, detail="Centroide inválido (NaN).")

        # =========================================================
        # 🔥 DETECÇÃO DE SISTEMA LOCAL (MEMORIAL / SEGMENTOS)
        # =========================================================
        minx, miny, maxx, maxy = geom.bounds

        is_local = (
            abs(minx) < 1000
            and abs(miny) < 1000
            and abs(maxx) < 1000
            and abs(maxy) < 1000
        )

        if is_local:
            # 🚀 NÃO PROJETAR → já está em sistema plano
            area_m2 = GeometriaService._safe_float(geom.area)
            perimetro_m = GeometriaService._safe_float(geom.length)
            area_ha = GeometriaService._safe_float(area_m2 / 10000.0)

            return 0, area_ha, perimetro_m

        # =========================================================
        # 🔥 FLUXO GEOGRÁFICO NORMAL (WGS84 → UTM)
        # =========================================================
        if epsg_origem <= 0:
            raise HTTPException(status_code=400, detail="EPSG de origem inválido.")

        epsg_utm = GeometriaService._utm_epsg_from_lonlat(lon, lat)

        try:
            crs_src = CRS.from_epsg(epsg_origem)
            crs_dst = CRS.from_epsg(epsg_utm)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Erro ao definir CRS.") from exc

        transformer = Transformer.from_crs(crs_src, crs_dst, always_xy=True)

        coords = list(geom.exterior.coords)

        proj_coords = []
        for x, y in coords:
            try:
                X, Y = transformer.transform(float(x), float(y))

                X = GeometriaService._safe_float(X)
                Y = GeometriaService._safe_float(Y)

                proj_coords.append((X, Y))
            except Exception:
                continue

        if len(proj_coords) < 4:
            raise HTTPException(
                status_code=400,
                detail="Falha ao projetar coordenadas suficientes.",
            )

        geom_utm = Polygon(proj_coords)

        if geom_utm.is_empty or not geom_utm.is_valid:
            geom_utm = geom_utm.buffer(0)

        if geom_utm.is_empty or not geom_utm.is_valid:
            raise HTTPException(
                status_code=400,
                detail="Falha ao projetar a geometria (UTM inválida).",
            )

        area_m2 = GeometriaService._safe_float(geom_utm.area)
        perimetro_m = GeometriaService._safe_float(geom_utm.length)

        area_ha = GeometriaService._safe_float(area_m2 / 10000.0)

        return epsg_utm, area_ha, perimetro_m