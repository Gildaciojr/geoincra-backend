from __future__ import annotations

import json
import math
import os
from datetime import datetime
from math import floor
from typing import Any

from fastapi import HTTPException
from pyproj import CRS, Transformer
from shapely.geometry import MultiPolygon, Polygon, shape


class GeometriaService:

    GEO_LON_MIN = -180.0
    GEO_LON_MAX = 180.0
    GEO_LAT_MIN = -90.0
    GEO_LAT_MAX = 90.0

    # =========================================================
    # UTM EPSG
    # =========================================================
    @staticmethod
    def _utm_epsg_from_lonlat(lon: float, lat: float) -> int:
        if not (GeometriaService.GEO_LON_MIN <= lon <= GeometriaService.GEO_LON_MAX):
            raise HTTPException(status_code=400, detail=f"Longitude inválida: {lon}")

        if not (GeometriaService.GEO_LAT_MIN <= lat <= GeometriaService.GEO_LAT_MAX):
            raise HTTPException(status_code=400, detail=f"Latitude inválida: {lat}")

        zona = int(floor((lon + 180.0) / 6.0) + 1)

        if zona < 1 or zona > 60:
            raise HTTPException(status_code=400, detail=f"Zona UTM inválida: {zona}")

        return (32600 + zona) if lat >= 0 else (32700 + zona)

    # =========================================================
    # SAFE FLOAT
    # =========================================================
    @staticmethod
    def _safe_float(value: float) -> float:
        try:
            v = float(value)
            if math.isnan(v) or math.isinf(v):
                return 0.0
            return v
        except Exception:
            return 0.0

    # =========================================================
    # HELPERS DE GEOMETRIA
    # =========================================================
    @staticmethod
    def _coords_anel_fechado(coords: list[tuple[float, float]]) -> list[tuple[float, float]]:
        if not coords:
            return []

        if coords[0] != coords[-1]:
            return coords + [coords[0]]

        return coords

    @staticmethod
    def _count_vertices(geom: Polygon) -> int:
        try:
            coords = list(geom.exterior.coords)
            return max(0, len(coords) - 1)
        except Exception:
            return 0

    @staticmethod
    def _bbox_info(geom: Polygon) -> dict[str, float]:
        minx, miny, maxx, maxy = geom.bounds
        return {
            "minx": float(minx),
            "miny": float(miny),
            "maxx": float(maxx),
            "maxy": float(maxy),
            "spanx": float(maxx - minx),
            "spany": float(maxy - miny),
        }

    @staticmethod
    def _coordenadas_parecem_geograficas(geom: Polygon) -> bool:
        bounds = GeometriaService._bbox_info(geom)

        return (
            GeometriaService.GEO_LON_MIN <= bounds["minx"] <= GeometriaService.GEO_LON_MAX
            and GeometriaService.GEO_LON_MIN <= bounds["maxx"] <= GeometriaService.GEO_LON_MAX
            and GeometriaService.GEO_LAT_MIN <= bounds["miny"] <= GeometriaService.GEO_LAT_MAX
            and GeometriaService.GEO_LAT_MIN <= bounds["maxy"] <= GeometriaService.GEO_LAT_MAX
        )

    @staticmethod
    def _corrigir_geometria(geom: Polygon) -> Polygon:
        if geom.is_valid and not geom.is_empty:
            return geom

        geom_corrigida = geom.buffer(0)

        if geom_corrigida.is_empty or not geom_corrigida.is_valid:
            raise HTTPException(
                status_code=400,
                detail="Geometria inválida após correção.",
            )

        if isinstance(geom_corrigida, Polygon):
            return geom_corrigida

        if isinstance(geom_corrigida, MultiPolygon):
            partes = sorted(geom_corrigida.geoms, key=lambda g: g.area, reverse=True)
            if not partes:
                raise HTTPException(
                    status_code=400,
                    detail="Geometria inválida após correção.",
                )
            return partes[0]

        raise HTTPException(
            status_code=400,
            detail="Geometria corrigida não resultou em POLYGON.",
        )

    # =========================================================
    # PARSE GEOJSON
    # =========================================================
    @staticmethod
    def _parse_polygon_geojson(geojson: str) -> Polygon:
        try:
            obj = json.loads(geojson)
            geom = shape(obj)
        except Exception as exc:
            raise HTTPException(status_code=400, detail="GeoJSON inválido.") from exc

        if geom.is_empty:
            raise HTTPException(status_code=400, detail="Geometria vazia.")

        if isinstance(geom, MultiPolygon):
            partes = sorted(geom.geoms, key=lambda g: g.area, reverse=True)
            if not partes:
                raise HTTPException(status_code=400, detail="Geometria MULTIPOLYGON vazia.")
            geom = partes[0]

        if not isinstance(geom, Polygon):
            raise HTTPException(status_code=400, detail="Geometria deve ser POLYGON.")

        coords = list(geom.exterior.coords)

        if len(coords) < 4:
            raise HTTPException(
                status_code=400,
                detail="Polígono inválido (menos de 4 vértices).",
            )

        coords = GeometriaService._coords_anel_fechado(
            [(float(x), float(y)) for x, y in coords]
        )
        geom = Polygon(coords)

        geom = GeometriaService._corrigir_geometria(geom)

        coords_validos = list(geom.exterior.coords)
        if len(coords_validos) < 4:
            raise HTTPException(
                status_code=400,
                detail="Polígono inválido após correção (menos de 4 vértices).",
            )

        return geom

    # =========================================================
    # ANALISAR REFERENCIAL
    # =========================================================
    @staticmethod
    def analisar_referencial(
        geojson: str,
        epsg_origem: int | None = 4326,
    ) -> dict[str, Any]:

        geom = GeometriaService._parse_polygon_geojson(geojson)

        bounds = GeometriaService._bbox_info(geom)
        spanx = bounds["spanx"]
        spany = bounds["spany"]

        centroid = geom.centroid
        cx = float(centroid.x)
        cy = float(centroid.y)

        if math.isnan(cx) or math.isnan(cy):
            raise HTTPException(status_code=400, detail="Centroide inválido (NaN).")

        faixa_geografica_valida = GeometriaService._coordenadas_parecem_geograficas(geom)

        # Heurística:
        # se a geometria parece geográfica e está em escala compatível com graus,
        # tratamos como GEOGRAFICA; caso contrário, LOCAL_CARTESIANA.
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
            "bounds": bounds,
            "centroid": {
                "x": cx,
                "y": cy,
            },
            "vertices": GeometriaService._count_vertices(geom),
            "area_bruta_unidades": GeometriaService._safe_float(geom.area),
            "perimetro_bruto_unidades": GeometriaService._safe_float(geom.length),
            "faixa_geografica_valida": faixa_geografica_valida,
            "escala_graus_valida": escala_graus,
        }

    # =========================================================
    # CALCULAR AREA E PERIMETRO
    # =========================================================
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

        if not (
            GeometriaService.GEO_LON_MIN <= lon <= GeometriaService.GEO_LON_MAX
            and GeometriaService.GEO_LAT_MIN <= lat <= GeometriaService.GEO_LAT_MAX
        ):
            return None, GeometriaService._safe_float(geom.area) / 10000.0, GeometriaService._safe_float(geom.length)

        epsg_utm = GeometriaService._utm_epsg_from_lonlat(lon, lat)

        try:
            transformer = Transformer.from_crs(
                CRS.from_epsg(epsg_origem),
                CRS.from_epsg(epsg_utm),
                always_xy=True,
            )
        except Exception:
            return None, GeometriaService._safe_float(geom.area) / 10000.0, GeometriaService._safe_float(geom.length)

        proj_coords: list[tuple[float, float]] = []

        for x, y in geom.exterior.coords:
            x = float(x)
            y = float(y)

            if not (
                GeometriaService.GEO_LON_MIN <= x <= GeometriaService.GEO_LON_MAX
                and GeometriaService.GEO_LAT_MIN <= y <= GeometriaService.GEO_LAT_MAX
            ):
                continue

            try:
                X, Y = transformer.transform(x, y)
            except Exception:
                continue

            if math.isnan(X) or math.isnan(Y) or math.isinf(X) or math.isinf(Y):
                continue

            proj_coords.append((float(X), float(Y)))

        if len(proj_coords) < 4:
            return None, GeometriaService._safe_float(geom.area) / 10000.0, GeometriaService._safe_float(geom.length)

        proj_coords = GeometriaService._coords_anel_fechado(proj_coords)
        geom_utm = Polygon(proj_coords)

        try:
            geom_utm = GeometriaService._corrigir_geometria(geom_utm)
        except Exception:
            return None, GeometriaService._safe_float(geom.area) / 10000.0, GeometriaService._safe_float(geom.length)

        area_m2 = GeometriaService._safe_float(geom_utm.area)
        perimetro_m = GeometriaService._safe_float(geom_utm.length)

        return epsg_utm, area_m2 / 10000.0, perimetro_m

    # =========================================================
    # EXPORTAR GEOJSON PARA ARQUIVO
    # =========================================================
    @staticmethod
    def exportar_geojson(imovel_id: int, geojson: str) -> dict:
        pasta = f"app/uploads/imoveis/{imovel_id}/geometria"
        os.makedirs(pasta, exist_ok=True)

        timestamp = int(datetime.utcnow().timestamp())
        nome_arquivo = f"geometria_{timestamp}.geojson"
        caminho = f"{pasta}/{nome_arquivo}"

        try:
            parsed = json.loads(geojson)
            with open(caminho, "w", encoding="utf-8") as f:
                json.dump(parsed, f, ensure_ascii=False, indent=2)
        except Exception:
            with open(caminho, "w", encoding="utf-8") as f:
                f.write(geojson)

        base_url = "https://geoincra.escriturafacil.com"
        url = f"{base_url}/{caminho.replace('app/', '')}"

        return {
            "success": True,
            "arquivo_path": caminho,
            "arquivo_url": url,
        }