from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime
from math import atan2, degrees, sqrt, floor
from typing import List, Tuple

from fastapi import HTTPException
from pyproj import CRS, Transformer
from shapely.geometry import shape, Polygon


@dataclass(frozen=True)
class _PontoUTM:
    x: float
    y: float


class MemorialService:

    @staticmethod
    def _safe_float(value):
        try:
            v = float(value)
            if math.isnan(v) or math.isinf(v):
                return 0.0
            return v
        except Exception:
            return 0.0

    @staticmethod
    def _utm_epsg_from_lonlat(lon: float, lat: float) -> int:
        zona = int(floor((lon + 180.0) / 6.0) + 1)
        return 32600 + zona if lat >= 0 else 32700 + zona

    @staticmethod
    def _to_utm_points(geojson: str) -> Tuple[int, List[_PontoUTM], Polygon]:
        try:
            geom = shape(json.loads(geojson))
        except Exception as exc:
            raise HTTPException(status_code=400, detail="GeoJSON inválido.") from exc

        if not isinstance(geom, Polygon):
            raise HTTPException(status_code=400, detail="Geometria deve ser POLYGON.")

        if geom.is_empty:
            raise HTTPException(status_code=400, detail="Geometria vazia.")

        if not geom.is_valid:
            geom = geom.buffer(0)

        if geom.is_empty or not geom.is_valid:
            raise HTTPException(status_code=400, detail="Geometria inválida.")

        centroid = geom.centroid

        lon = float(centroid.x)
        lat = float(centroid.y)

        if math.isnan(lon) or math.isnan(lat):
            raise HTTPException(status_code=400, detail="Centroide inválido.")

        epsg_utm = MemorialService._utm_epsg_from_lonlat(lon, lat)

        transformer = Transformer.from_crs(
            CRS.from_epsg(4326),
            CRS.from_epsg(epsg_utm),
            always_xy=True,
        )

        coords = list(geom.exterior.coords)

        if coords[0] != coords[-1]:
            coords.append(coords[0])

        pts_utm = []

        for x, y in coords:
            X, Y = transformer.transform(float(x), float(y))
            X = MemorialService._safe_float(X)
            Y = MemorialService._safe_float(Y)
            pts_utm.append(_PontoUTM(X, Y))

        return epsg_utm, pts_utm, geom

    @staticmethod
    def _dist_m(p1: _PontoUTM, p2: _PontoUTM) -> float:
        return MemorialService._safe_float(
            sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2)
        )

    @staticmethod
    def _azimute_deg(p1: _PontoUTM, p2: _PontoUTM) -> float:
        dx = p2.x - p1.x
        dy = p2.y - p1.y
        ang = degrees(atan2(dx, dy))
        if ang < 0:
            ang += 360
        return MemorialService._safe_float(ang)

    @staticmethod
    def _deg_to_dms_str(deg: float) -> str:
        d = int(deg)
        m = int((deg - d) * 60)
        s = ((deg - d) * 60 - m) * 60
        return f"{d:02d}°{m:02d}'{s:05.2f}\""

    @staticmethod
    def _rumo_from_azimute(az: float) -> str:
        az = az % 360
        if az < 90:
            return f"N {MemorialService._deg_to_dms_str(az)} E"
        if az < 180:
            return f"S {MemorialService._deg_to_dms_str(180 - az)} E"
        if az < 270:
            return f"S {MemorialService._deg_to_dms_str(az - 180)} W"
        return f"N {MemorialService._deg_to_dms_str(360 - az)} W"

    @staticmethod
    def gerar_memorial(
        geometria_id: int,
        geojson: str,
        area_hectares: float,
        perimetro_m: float,
        prefixo_vertice: str = "V",
    ) -> dict:

        epsg_utm, pts, _ = MemorialService._to_utm_points(geojson)

        linhas = []

        for i in range(len(pts) - 1):
            p1 = pts[i]
            p2 = pts[i + 1]

            dist = MemorialService._dist_m(p1, p2)
            az = MemorialService._azimute_deg(p1, p2)

            linhas.append(
                {
                    "ordem": i + 1,
                    "de_vertice": f"{prefixo_vertice}{i+1}",
                    "ate_vertice": f"{prefixo_vertice}{i+2}" if i + 1 < len(pts) - 1 else f"{prefixo_vertice}1",
                    "azimute_graus": az,
                    "rumo": MemorialService._rumo_from_azimute(az),
                    "distancia_m": dist,
                }
            )

        area_hectares = MemorialService._safe_float(area_hectares)
        perimetro_m = MemorialService._safe_float(perimetro_m)

        return {
            "geometria_id": geometria_id,
            "epsg_utm": epsg_utm,
            "area_hectares": area_hectares,
            "perimetro_m": perimetro_m,
            "linhas": linhas,
            "texto": "Memorial gerado automaticamente",
            "gerado_em": datetime.utcnow(),
        }