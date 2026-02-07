from __future__ import annotations

import json
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
        if geom.is_empty or not geom.is_valid:
            raise HTTPException(status_code=400, detail="Geometria vazia ou inválida.")
        return geom

    @staticmethod
    def calcular_area_perimetro(
        geojson: str,
        epsg_origem: int = 4326,
    ) -> Tuple[int, float, float]:
        """
        Retorna: (epsg_utm, area_ha, perimetro_m)
        - Converte a geometria para UTM apropriado (pela posição do centróide)
        - Calcula área (ha) e perímetro (m) em UTM (metros)
        """
        geom = GeometriaService._parse_polygon_geojson(geojson)

        # Se origem não for 4326, você pode manter — mas aqui o padrão do projeto é 4326.
        # Não quebramos, apenas validamos que é EPSG numérico.
        if epsg_origem <= 0:
            raise HTTPException(status_code=400, detail="EPSG de origem inválido.")

        centroid = geom.centroid
        lon = float(centroid.x)
        lat = float(centroid.y)

        epsg_utm = GeometriaService._utm_epsg_from_lonlat(lon, lat)

        crs_src = CRS.from_epsg(epsg_origem)
        crs_dst = CRS.from_epsg(epsg_utm)
        transformer = Transformer.from_crs(crs_src, crs_dst, always_xy=True)

        # Projetar coords do exterior
        coords = list(geom.exterior.coords)
        proj_coords = [transformer.transform(float(x), float(y)) for x, y in coords]
        geom_utm = Polygon(proj_coords)

        if geom_utm.is_empty or not geom_utm.is_valid:
            raise HTTPException(status_code=400, detail="Falha ao projetar a geometria (UTM inválida).")

        area_m2 = float(geom_utm.area)
        perimetro_m = float(geom_utm.length)

        area_ha = area_m2 / 10000.0

        return epsg_utm, area_ha, perimetro_m
