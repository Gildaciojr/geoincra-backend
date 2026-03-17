from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime
from math import atan2, degrees, floor, sqrt
from typing import List, Optional, Tuple

from fastapi import HTTPException
from pyproj import CRS, Transformer
from shapely.geometry import Polygon, shape

from app.services.geometria_service import GeometriaService


@dataclass(frozen=True)
class _PontoPlano:
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
    def _parse_polygon(geojson: str) -> Polygon:
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

        return geom

    @staticmethod
    def _to_points(
        geojson: str,
        epsg_origem: int | None = 4326,
    ) -> Tuple[Optional[int], List[_PontoPlano], str]:
        analise = GeometriaService.analisar_referencial(
            geojson=geojson,
            epsg_origem=epsg_origem,
        )

        geom: Polygon = analise["geom"]
        tipo_referencial = str(analise["tipo_referencial"])

        coords = list(geom.exterior.coords)
        if coords[0] != coords[-1]:
            coords.append(coords[0])

        if tipo_referencial == "LOCAL_CARTESIANA":
            pontos_locais = [
                _PontoPlano(
                    x=MemorialService._safe_float(x),
                    y=MemorialService._safe_float(y),
                )
                for x, y in coords
            ]
            return None, pontos_locais, tipo_referencial

        if epsg_origem is None or epsg_origem <= 0:
            raise HTTPException(
                status_code=400,
                detail="EPSG de origem inválido para memorial geográfico.",
            )

        lon = float(analise["centroid"]["x"])
        lat = float(analise["centroid"]["y"])
        epsg_utm = MemorialService._utm_epsg_from_lonlat(lon, lat)

        transformer = Transformer.from_crs(
            CRS.from_epsg(epsg_origem),
            CRS.from_epsg(epsg_utm),
            always_xy=True,
        )

        pontos_utm: list[_PontoPlano] = []
        for x, y in coords:
            X, Y = transformer.transform(float(x), float(y))
            pontos_utm.append(
                _PontoPlano(
                    x=MemorialService._safe_float(X),
                    y=MemorialService._safe_float(Y),
                )
            )

        return epsg_utm, pontos_utm, tipo_referencial

    @staticmethod
    def _dist_m(p1: _PontoPlano, p2: _PontoPlano) -> float:
        return MemorialService._safe_float(
            sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2)
        )

    @staticmethod
    def _azimute_deg(p1: _PontoPlano, p2: _PontoPlano) -> float:
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
    def _montar_texto_memorial(
        linhas: list[dict],
        tipo_referencial: str,
        epsg_utm: int | None,
        area_hectares: float,
        perimetro_m: float,
    ) -> str:
        cabecalho = [
            "MEMORIAL DESCRITIVO",
            "",
            f"Referencial: {tipo_referencial}",
            f"EPSG UTM: {epsg_utm if epsg_utm is not None else 'N/A'}",
            f"Área (ha): {area_hectares:.4f}",
            f"Perímetro (m): {perimetro_m:.3f}",
            "",
            "Segmentos:",
        ]

        corpo: list[str] = []
        for linha in linhas:
            corpo.append(
                f"{linha['ordem']:02d}. "
                f"{linha['de_vertice']} -> {linha['ate_vertice']} | "
                f"Azimute: {linha['azimute_graus']:.6f}° | "
                f"Rumo: {linha['rumo']} | "
                f"Distância: {linha['distancia_m']:.3f} m"
            )

        return "\n".join(cabecalho + corpo)

    @staticmethod
    def gerar_memorial(
        geometria_id: int,
        geojson: str,
        area_hectares: float,
        perimetro_m: float,
        prefixo_vertice: str = "V",
        epsg_origem: int | None = 4326,
    ) -> dict:
        epsg_utm, pts, tipo_referencial = MemorialService._to_points(
            geojson=geojson,
            epsg_origem=epsg_origem,
        )

        linhas = []

        for i in range(len(pts) - 1):
            p1 = pts[i]
            p2 = pts[i + 1]

            dist = MemorialService._dist_m(p1, p2)
            az = MemorialService._azimute_deg(p1, p2)

            linhas.append(
                {
                    "ordem": i + 1,
                    "de_vertice": f"{prefixo_vertice}{i + 1}",
                    "ate_vertice": (
                        f"{prefixo_vertice}{i + 2}"
                        if i + 1 < len(pts) - 1
                        else f"{prefixo_vertice}1"
                    ),
                    "azimute_graus": az,
                    "rumo": MemorialService._rumo_from_azimute(az),
                    "distancia_m": dist,
                }
            )

        area_hectares = MemorialService._safe_float(area_hectares)
        perimetro_m = MemorialService._safe_float(perimetro_m)

        texto = MemorialService._montar_texto_memorial(
            linhas=linhas,
            tipo_referencial=tipo_referencial,
            epsg_utm=epsg_utm,
            area_hectares=area_hectares,
            perimetro_m=perimetro_m,
        )

        return {
            "geometria_id": geometria_id,
            "epsg_utm": epsg_utm,
            "tipo_referencial": tipo_referencial,
            "area_hectares": area_hectares,
            "perimetro_m": perimetro_m,
            "linhas": linhas,
            "texto": texto,
            "gerado_em": datetime.utcnow(),
        }