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
            "minx": GeometriaService._safe_float(minx),
            "miny": GeometriaService._safe_float(miny),
            "maxx": GeometriaService._safe_float(maxx),
            "maxy": GeometriaService._safe_float(maxy),
            "spanx": GeometriaService._safe_float(maxx - minx),
            "spany": GeometriaService._safe_float(maxy - miny),
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
    def _selecionar_maior_polygon(geom: MultiPolygon) -> Polygon:
        partes = sorted(geom.geoms, key=lambda g: g.area, reverse=True)

        if not partes:
            raise HTTPException(
                status_code=400,
                detail="Geometria MULTIPOLYGON vazia.",
            )

        maior = partes[0]

        if maior.is_empty:
            raise HTTPException(
                status_code=400,
                detail="Geometria MULTIPOLYGON inválida.",
            )

        return maior

    @staticmethod
    def _corrigir_geometria(geom: Polygon | MultiPolygon) -> Polygon:
        if geom.is_valid and not geom.is_empty:
            if isinstance(geom, Polygon):
                return geom

            if isinstance(geom, MultiPolygon):
                return GeometriaService._selecionar_maior_polygon(geom)

        geom_corrigida = geom.buffer(0)

        if geom_corrigida.is_empty or not geom_corrigida.is_valid:
            raise HTTPException(
                status_code=400,
                detail="Geometria inválida após correção.",
            )

        if isinstance(geom_corrigida, Polygon):
            return geom_corrigida

        if isinstance(geom_corrigida, MultiPolygon):
            return GeometriaService._selecionar_maior_polygon(geom_corrigida)

        raise HTTPException(
            status_code=400,
            detail="Geometria corrigida não resultou em POLYGON.",
        )

    @staticmethod
    def _normalizar_geojson_input(geojson: Any) -> dict[str, Any]:
        if geojson is None:
            raise HTTPException(status_code=400, detail="GeoJSON ausente.")

        if isinstance(geojson, dict):
            return geojson

        if isinstance(geojson, str):
            texto = geojson.strip()
            if not texto:
                raise HTTPException(status_code=400, detail="GeoJSON vazio.")
            try:
                return json.loads(texto)
            except Exception as exc:
                raise HTTPException(status_code=400, detail="GeoJSON inválido.") from exc

        raise HTTPException(status_code=400, detail="GeoJSON em formato inválido.")

    @staticmethod
    def _sanear_coords(coords: list[tuple[float, float]]) -> list[tuple[float, float]]:
        coords_saneados: list[tuple[float, float]] = []

        for x, y in coords:
            xf = GeometriaService._safe_float(x)
            yf = GeometriaService._safe_float(y)

            if math.isnan(xf) or math.isnan(yf) or math.isinf(xf) or math.isinf(yf):
                continue

            coords_saneados.append((xf, yf))

        return coords_saneados

    # =========================================================
    # NORMALIZAÇÃO PÚBLICA DE GEOMETRIA
    # =========================================================
    @staticmethod
    def parse_geometry_or_raise(geojson: Any):
        try:
            obj = GeometriaService._normalizar_geojson_input(geojson)
            geom = shape(obj)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=400, detail="GeoJSON inválido.") from exc

        if geom.is_empty:
            raise HTTPException(status_code=400, detail="Geometria vazia.")

        return geom

    @staticmethod
    def normalizar_para_polygon(geojson: Any) -> Polygon:
        geom = GeometriaService.parse_geometry_or_raise(geojson)

        if isinstance(geom, MultiPolygon):
            geom = GeometriaService._selecionar_maior_polygon(geom)

        if not isinstance(geom, Polygon):
            raise HTTPException(status_code=400, detail="Geometria deve ser POLYGON.")

        coords = list(geom.exterior.coords)
        coords = GeometriaService._sanear_coords(
            [(float(x), float(y)) for x, y in coords]
        )

        if len(coords) < 4:
            raise HTTPException(
                status_code=400,
                detail="Polígono inválido (menos de 4 vértices).",
            )

        coords = GeometriaService._coords_anel_fechado(coords)
        geom = Polygon(coords)

        geom = GeometriaService._corrigir_geometria(geom)

        coords_validos = GeometriaService._sanear_coords(list(geom.exterior.coords))
        if len(coords_validos) < 4:
            raise HTTPException(
                status_code=400,
                detail="Polígono inválido após correção (menos de 4 vértices).",
            )

        return geom

    @staticmethod
    def parse_polygon_or_raise(geojson: Any) -> Polygon:
        return GeometriaService.normalizar_para_polygon(geojson)

    # =========================================================
    # PARSE GEOJSON
    # =========================================================
    @staticmethod
    def _parse_polygon_geojson(geojson: Any) -> Polygon:
        return GeometriaService.parse_polygon_or_raise(geojson)

    # =========================================================
    # ANALISAR REFERENCIAL
    # =========================================================
    @staticmethod
    def analisar_referencial(
        geojson: Any,
        epsg_origem: int | None = 4326,
    ) -> dict[str, Any]:

        geom = GeometriaService._parse_polygon_geojson(geojson)

        bounds = GeometriaService._bbox_info(geom)
        spanx = bounds["spanx"]
        spany = bounds["spany"]

        centroid = geom.centroid
        cx = GeometriaService._safe_float(centroid.x)
        cy = GeometriaService._safe_float(centroid.y)

        if math.isnan(cx) or math.isnan(cy) or math.isinf(cx) or math.isinf(cy):
            raise HTTPException(status_code=400, detail="Centroide inválido (NaN/Inf).")

        faixa_geografica_valida = GeometriaService._coordenadas_parecem_geograficas(geom)

        # Heurística:
        # - se EPSG <= 0: LOCAL_CARTESIANA
        # - se bounds não parecem geográficos: LOCAL_CARTESIANA
        # - se escala em graus é desproporcional: LOCAL_CARTESIANA
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
        geojson: Any,
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

        lon = GeometriaService._safe_float(analise["centroid"]["x"])
        lat = GeometriaService._safe_float(analise["centroid"]["y"])

        if not (
            GeometriaService.GEO_LON_MIN <= lon <= GeometriaService.GEO_LON_MAX
            and GeometriaService.GEO_LAT_MIN <= lat <= GeometriaService.GEO_LAT_MAX
        ):
            return (
                None,
                GeometriaService._safe_float(geom.area) / 10000.0,
                GeometriaService._safe_float(geom.length),
            )

        epsg_utm = GeometriaService._utm_epsg_from_lonlat(lon, lat)

        try:
            transformer = Transformer.from_crs(
                CRS.from_epsg(epsg_origem),
                CRS.from_epsg(epsg_utm),
                always_xy=True,
            )
        except Exception:
            return (
                None,
                GeometriaService._safe_float(geom.area) / 10000.0,
                GeometriaService._safe_float(geom.length),
            )

        proj_coords: list[tuple[float, float]] = []

        for x, y in geom.exterior.coords:
            x = GeometriaService._safe_float(x)
            y = GeometriaService._safe_float(y)

            if not (
                GeometriaService.GEO_LON_MIN <= x <= GeometriaService.GEO_LON_MAX
                and GeometriaService.GEO_LAT_MIN <= y <= GeometriaService.GEO_LAT_MAX
            ):
                continue

            try:
                X, Y = transformer.transform(x, y)
            except Exception:
                continue

            X = GeometriaService._safe_float(X)
            Y = GeometriaService._safe_float(Y)

            if math.isnan(X) or math.isnan(Y) or math.isinf(X) or math.isinf(Y):
                continue

            proj_coords.append((X, Y))

        if len(proj_coords) < 4:
            return (
                None,
                GeometriaService._safe_float(geom.area) / 10000.0,
                GeometriaService._safe_float(geom.length),
            )

        proj_coords = GeometriaService._coords_anel_fechado(proj_coords)
        geom_utm = Polygon(proj_coords)

        try:
            geom_utm = GeometriaService._corrigir_geometria(geom_utm)
        except Exception:
            return (
                None,
                GeometriaService._safe_float(geom.area) / 10000.0,
                GeometriaService._safe_float(geom.length),
            )

        area_m2 = GeometriaService._safe_float(geom_utm.area)
        perimetro_m = GeometriaService._safe_float(geom_utm.length)

        return epsg_utm, area_m2 / 10000.0, perimetro_m

    # =========================================================
    # EXPORTAR GEOJSON PARA ARQUIVO
    # =========================================================
    @staticmethod
    def exportar_geojson(imovel_id: int, geojson: Any) -> dict:
        pasta = f"app/uploads/imoveis/{imovel_id}/geometria"
        os.makedirs(pasta, exist_ok=True)

        timestamp = int(datetime.utcnow().timestamp())
        nome_arquivo = f"geometria_{timestamp}.geojson"
        caminho = f"{pasta}/{nome_arquivo}"

        try:
            if isinstance(geojson, dict):
                parsed = geojson
            else:
                parsed = json.loads(geojson)

            with open(caminho, "w", encoding="utf-8") as f:
                json.dump(parsed, f, ensure_ascii=False, indent=2)

        except Exception:
            with open(caminho, "w", encoding="utf-8") as f:
                f.write(str(geojson))

        base_url = "https://geoincra.escriturafacil.com"
        url = f"{base_url}/{caminho.replace('app/', '')}"

        return {
            "success": True,
            "arquivo_path": caminho,
            "arquivo_url": url,
        }

    # =========================================================
    # ENGENHARIA DE SEGMENTOS (NOVO BLOCO)
    # =========================================================
    @staticmethod
    def _calcular_azimute(dx: float, dy: float) -> float:
        """
        Azimute geodésico simplificado:
        0° = Norte, sentido horário
        """
        if dx == 0 and dy == 0:
            return 0.0

        az = math.degrees(math.atan2(dx, dy))
        return (az + 360.0) % 360.0

    @staticmethod
    def _calcular_distancia(x1: float, y1: float, x2: float, y2: float) -> float:
        dx = x2 - x1
        dy = y2 - y1
        return math.sqrt(dx * dx + dy * dy)

    # =========================================================
    # EXTRAÇÃO DE SEGMENTOS (NÍVEL ENGENHARIA)
    # =========================================================
    @staticmethod
    def extract_segmentos(geojson: Any) -> list[dict[str, Any]]:
        geom = GeometriaService.parse_polygon_or_raise(geojson)

        coords = list(geom.exterior.coords)

        if len(coords) < 4:
            raise HTTPException(
                status_code=400,
                detail="Polígono inválido para extração de segmentos.",
            )

        # =========================================================
        # 🔥 SANEAR COORDENADAS
        # =========================================================
        coords = [
            (
                GeometriaService._safe_float(x),
                GeometriaService._safe_float(y),
            )
            for x, y in coords
        ]

        # =========================================================
        # 🔥 GARANTIR FECHAMENTO
        # =========================================================
        if coords[0] != coords[-1]:
            coords.append(coords[0])

        # =========================================================
        # 🔥 NORMALIZAÇÃO DE ORIENTAÇÃO (CRÍTICO)
        # Garante sentido anti-horário (padrão técnico consistente)
        # =========================================================
        try:
            if not geom.exterior.is_ccw:
                coords = list(reversed(coords))
        except Exception:
            pass  # fallback seguro sem quebrar execução

        segmentos: list[dict[str, Any]] = []

        # =========================================================
        # EXTRAÇÃO SEGMENTADA
        # =========================================================
        for i in range(len(coords) - 1):

            x1, y1 = coords[i]
            x2, y2 = coords[i + 1]

            # proteção adicional
            if (
                math.isnan(x1) or math.isnan(y1)
                or math.isnan(x2) or math.isnan(y2)
                or math.isinf(x1) or math.isinf(y1)
                or math.isinf(x2) or math.isinf(y2)
            ):
                continue

            dx = x2 - x1
            dy = y2 - y1

            # =====================================================
            # 🔥 EVITA SEGMENTOS DEGENERADOS
            # =====================================================
            if dx == 0 and dy == 0:
                continue

            distancia = GeometriaService._calcular_distancia(x1, y1, x2, y2)
            azimute = GeometriaService._calcular_azimute(dx, dy)

            segmentos.append({
                "indice": len(segmentos) + 1,
                "ponto_inicial": {"x": x1, "y": y1},
                "ponto_final": {"x": x2, "y": y2},
                "distancia": GeometriaService._safe_float(distancia),
                "azimute_graus": GeometriaService._safe_float(azimute),
            })

        if not segmentos:
            raise HTTPException(
                status_code=400,
                detail="Não foi possível extrair segmentos válidos da geometria.",
            )

        return segmentos

    # =========================================================
    # EXTRAÇÃO DE VÉRTICES (PARA MEMORIAL / CROQUI / CAD)
    # =========================================================
    @staticmethod
    def extract_vertices_enriquecidos(geojson: Any) -> list[dict[str, Any]]:
        segmentos = GeometriaService.extract_segmentos(geojson)

        vertices = []

        for seg in segmentos:
            vertices.append({
                "indice": seg["indice"],
                "x": seg["ponto_inicial"]["x"],
                "y": seg["ponto_inicial"]["y"],
                "distancia": seg["distancia"],
                "azimute_graus": seg["azimute_graus"],
            })

        return vertices