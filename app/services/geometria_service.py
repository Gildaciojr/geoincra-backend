from __future__ import annotations

import json
import math
from math import floor
from typing import Any

from fastapi import HTTPException
from pyproj import CRS, Transformer
from shapely.geometry import Polygon, shape


class GeometriaService:
    @staticmethod
    def _utm_epsg_from_lonlat(lon: float, lat: float) -> int:
        if not (-180.0 <= lon <= 180.0):
            raise HTTPException(status_code=400, detail=f"Longitude inválida: {lon}")

        if not (-90.0 <= lat <= 90.0):
            raise HTTPException(status_code=400, detail=f"Latitude inválida: {lat}")

        zona = int(floor((lon + 180.0) / 6.0) + 1)

        if zona < 1 or zona > 60:
            raise HTTPException(status_code=400, detail=f"Zona UTM inválida: {zona}")

        return (32600 + zona) if lat >= 0 else (32700 + zona)

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

        # 🔒 garantir anel válido
        coords = list(geom.exterior.coords)
        if len(coords) < 4:
            raise HTTPException(status_code=400, detail="Polígono inválido (menos de 4 vértices).")

        if coords[0] != coords[-1]:
            coords.append(coords[0])
            geom = Polygon(coords)

        if not geom.is_valid:
            geom = geom.buffer(0)

        if geom.is_empty or not geom.is_valid:
            raise HTTPException(
                status_code=400,
                detail="Geometria inválida após correção.",
            )

        return geom

    @staticmethod
    def analisar_referencial(
        geojson: str,
        epsg_origem: int | None = 4326,
    ) -> dict[str, Any]:
        geom = GeometriaService._parse_polygon_geojson(geojson)

        minx, miny, maxx, maxy = geom.bounds
        spanx = float(maxx - minx)
        spany = float(maxy - miny)

        centroid = geom.centroid
        cx = float(centroid.x)
        cy = float(centroid.y)

        if math.isnan(cx) or math.isnan(cy):
            raise HTTPException(status_code=400, detail="Centroide inválido (NaN).")

        faixa_geografica_valida = (
            -180 <= minx <= 180 and
            -180 <= maxx <= 180 and
            -90 <= miny <= 90 and
            -90 <= maxy <= 90
        )

        escala_graus = spanx < 5 and spany < 5

        if epsg_origem is not None and int(epsg_origem) <= 0:
            tipo = "LOCAL_CARTESIANA"
        elif not faixa_geografica_valida:
            tipo = "LOCAL_CARTESIANA"
        elif not escala_graus:
            tipo = "LOCAL_CARTESIANA"
        else:
            tipo = "GEOGRAFICA"

        return {
            "tipo_referencial": tipo,
            "geom": geom,
            "bounds": {
                "minx": float(minx),
                "miny": float(miny),
                "maxx": float(maxx),
                "maxy": float(maxy),
                "spanx": spanx,
                "spany": spany,
            },
            "centroid": {
                "x": cx,
                "y": cy,
            },
        }

    @staticmethod
    def calcular_area_perimetro(
        geojson: str,
        epsg_origem: int = 4326,
    ) -> tuple[int | None, float, float]:
        analise = GeometriaService.analisar_referencial(
            geojson=geojson,
            epsg_origem=epsg_origem,
        )

        geom: Polygon = analise["geom"]
        tipo_referencial = analise["tipo_referencial"]

        if tipo_referencial == "LOCAL_CARTESIANA":
            area_m2 = GeometriaService._safe_float(geom.area)
            perimetro_m = GeometriaService._safe_float(geom.length)
            return None, area_m2 / 10000.0, perimetro_m

        lon = float(analise["centroid"]["x"])
        lat = float(analise["centroid"]["y"])

        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            return None, geom.area / 10000.0, geom.length

        epsg_utm = GeometriaService._utm_epsg_from_lonlat(lon, lat)

        transformer = Transformer.from_crs(
            CRS.from_epsg(epsg_origem),
            CRS.from_epsg(epsg_utm),
            always_xy=True,
        )

        proj_coords = []
        for x, y in geom.exterior.coords:
            if not (-180 <= x <= 180 and -90 <= y <= 90):
                continue

            X, Y = transformer.transform(x, y)
            proj_coords.append((X, Y))

        if len(proj_coords) < 4:
            return None, geom.area / 10000.0, geom.length

        geom_utm = Polygon(proj_coords)

        if not geom_utm.is_valid:
            geom_utm = geom_utm.buffer(0)

        if geom_utm.is_empty or not geom_utm.is_valid:
            return None, geom.area / 10000.0, geom.length

        area_m2 = geom_utm.area
        perimetro_m = geom_utm.length

        return epsg_utm, area_m2 / 10000.0, perimetro_m