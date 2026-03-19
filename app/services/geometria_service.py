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

        # =========================================================
        # VALIDAÇÃO ROBUSTA DE REFERENCIAL
        # =========================================================
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

        # =========================================================
        # LOCAL → NÃO PROJETAR
        # =========================================================
        if tipo_referencial == "LOCAL_CARTESIANA":
            area_m2 = GeometriaService._safe_float(geom.area)
            perimetro_m = GeometriaService._safe_float(geom.length)
            area_ha = GeometriaService._safe_float(area_m2 / 10000.0)
            return None, area_ha, perimetro_m

        if epsg_origem <= 0:
            raise HTTPException(status_code=400, detail="EPSG de origem inválido.")

        lon = float(analise["centroid"]["x"])
        lat = float(analise["centroid"]["y"])

        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
            area_m2 = GeometriaService._safe_float(geom.area)
            perimetro_m = GeometriaService._safe_float(geom.length)
            area_ha = GeometriaService._safe_float(area_m2 / 10000.0)
            return None, area_ha, perimetro_m

        epsg_utm = GeometriaService._utm_epsg_from_lonlat(lon, lat)

        try:
            crs_src = CRS.from_epsg(epsg_origem)
            crs_dst = CRS.from_epsg(epsg_utm)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="Erro ao definir CRS.") from exc

        transformer = Transformer.from_crs(crs_src, crs_dst, always_xy=True)

        coords = list(geom.exterior.coords)
        proj_coords: list[tuple[float, float]] = []

        invalid_count = 0

        for x, y in coords:
            try:
                xf = float(x)
                yf = float(y)

                if not (-180 <= xf <= 180 and -90 <= yf <= 90):
                    invalid_count += 1
                    continue

                X, Y = transformer.transform(xf, yf)

                X = GeometriaService._safe_float(X)
                Y = GeometriaService._safe_float(Y)

                proj_coords.append((X, Y))

            except Exception:
                invalid_count += 1
                continue

        if len(proj_coords) < 4 or invalid_count > len(coords) * 0.3:
            area_m2 = GeometriaService._safe_float(geom.area)
            perimetro_m = GeometriaService._safe_float(geom.length)
            area_ha = GeometriaService._safe_float(area_m2 / 10000.0)
            return None, area_ha, perimetro_m

        geom_utm = Polygon(proj_coords)

        if geom_utm.is_empty:
            return None, GeometriaService._safe_float(geom.area / 10000.0), GeometriaService._safe_float(geom.length)

        if not geom_utm.is_valid:
            geom_utm = geom_utm.buffer(0)

        if geom_utm.is_empty or not geom_utm.is_valid:
            return None, GeometriaService._safe_float(geom.area / 10000.0), GeometriaService._safe_float(geom.length)

        area_m2 = GeometriaService._safe_float(geom_utm.area)
        perimetro_m = GeometriaService._safe_float(geom_utm.length)
        area_ha = GeometriaService._safe_float(area_m2 / 10000.0)

        return epsg_utm, area_ha, perimetro_m