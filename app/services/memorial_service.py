# app/services/memorial_service.py

from __future__ import annotations

import json
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
    """
    Gera memorial descritivo e croqui a partir de um GeoJSON (EPSG:4326).
    - Converte para UTM adequado (zona automática pelo centróide)
    - Calcula distâncias em metros e azimutes
    - Produz rumo padrão (quadrantal)
    """

    @staticmethod
    def _utm_epsg_from_lonlat(lon: float, lat: float) -> int:
        zona = int(floor((lon + 180.0) / 6.0) + 1)
        if lat >= 0:
            return 32600 + zona  # WGS84 / UTM North
        return 32700 + zona      # WGS84 / UTM South

    @staticmethod
    def _to_utm_points(geojson: str) -> Tuple[int, List[_PontoUTM], Polygon]:
        try:
            geom = shape(json.loads(geojson))
        except Exception as exc:
            raise HTTPException(status_code=400, detail="GeoJSON inválido.") from exc

        if not isinstance(geom, Polygon):
            raise HTTPException(status_code=400, detail="Geometria deve ser POLYGON.")

        if geom.is_empty or not geom.is_valid:
            raise HTTPException(status_code=400, detail="Geometria vazia ou inválida.")

        centroid = geom.centroid
        lon = float(centroid.x)
        lat = float(centroid.y)

        epsg_utm = MemorialService._utm_epsg_from_lonlat(lon, lat)

        crs_src = CRS.from_epsg(4326)
        crs_dst = CRS.from_epsg(epsg_utm)
        transformer = Transformer.from_crs(crs_src, crs_dst, always_xy=True)

        coords = list(geom.exterior.coords)
        if len(coords) < 4:
            raise HTTPException(status_code=400, detail="Polígono inválido (poucos vértices).")

        # Garantir fechamento
        if coords[0] != coords[-1]:
            coords.append(coords[0])

        pts_utm: List[_PontoUTM] = []
        for (x, y) in coords:
            X, Y = transformer.transform(float(x), float(y))
            pts_utm.append(_PontoUTM(x=float(X), y=float(Y)))

        return epsg_utm, pts_utm, geom

    @staticmethod
    def _dist_m(p1: _PontoUTM, p2: _PontoUTM) -> float:
        return float(sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2))

    @staticmethod
    def _azimute_deg(p1: _PontoUTM, p2: _PontoUTM) -> float:
        """
        Azimute a partir do Norte (0°) sentido horário até 360°.
        """
        dx = (p2.x - p1.x)
        dy = (p2.y - p1.y)
        # atan2(dx, dy) pois referência é o eixo Norte (dy)
        ang = degrees(atan2(dx, dy))
        if ang < 0:
            ang += 360.0
        return float(ang)

    @staticmethod
    def _deg_to_dms_str(deg: float) -> str:
        d = int(deg)
        m_float = (deg - d) * 60.0
        m = int(m_float)
        s = (m_float - m) * 60.0
        return f"{d:02d}°{m:02d}'{s:05.2f}\""

    @staticmethod
    def _rumo_from_azimute(az: float) -> str:
        """
        Converte azimute (0..360) para rumo quadrantal:
        N xx°xx'xx" E / N ... W / S ... E / S ... W
        """
        az = az % 360.0

        if 0.0 <= az < 90.0:
            ang = az
            return f"N {MemorialService._deg_to_dms_str(ang)} E"
        if 90.0 <= az < 180.0:
            ang = 180.0 - az
            return f"S {MemorialService._deg_to_dms_str(ang)} E"
        if 180.0 <= az < 270.0:
            ang = az - 180.0
            return f"S {MemorialService._deg_to_dms_str(ang)} W"
        ang = 360.0 - az
        return f"N {MemorialService._deg_to_dms_str(ang)} W"

    @staticmethod
    def gerar_memorial(
        geometria_id: int,
        geojson: str,
        area_hectares: float,
        perimetro_m: float,
        prefixo_vertice: str = "V",
    ) -> dict:
        epsg_utm, pts, _ = MemorialService._to_utm_points(geojson)

        # pts inclui o ponto final repetido (fechado)
        n_segmentos = len(pts) - 1
        if n_segmentos < 3:
            raise HTTPException(status_code=400, detail="Polígono insuficiente para memorial.")

        linhas = []
        for i in range(n_segmentos):
            p1 = pts[i]
            p2 = pts[i + 1]
            dist = MemorialService._dist_m(p1, p2)
            az = MemorialService._azimute_deg(p1, p2)
            rumo = MemorialService._rumo_from_azimute(az)

            linhas.append(
                {
                    "ordem": i + 1,
                    "de_vertice": f"{prefixo_vertice}{i+1}",
                    "ate_vertice": f"{prefixo_vertice}{i+2}" if i + 1 < n_segmentos else f"{prefixo_vertice}1",
                    "azimute_graus": az,
                    "rumo": rumo,
                    "distancia_m": float(dist),
                }
            )

        # Texto memorial
        now = datetime.utcnow()
        partes_txt = [
            "MEMORIAL DESCRITIVO",
            f"Geometria ID: {geometria_id}",
            f"Sistema de Referência: SIRGAS2000 / UTM (EPSG:{epsg_utm})",
            f"Área: {area_hectares:.4f} ha",
            f"Perímetro: {perimetro_m:.2f} m",
            "",
            "DESCRIÇÃO PERIMÉTRICA (RUMOS E DISTÂNCIAS):",
        ]

        for ln in linhas:
            partes_txt.append(
                f"{ln['ordem']:02d}) Do {ln['de_vertice']} ao {ln['ate_vertice']}: "
                f"Rumo {ln['rumo']} — Distância {ln['distancia_m']:.2f} m "
                f"(Azimute {ln['azimute_graus']:.6f}°)"
            )

        partes_txt.append("")
        partes_txt.append(f"Gerado em (UTC): {now.isoformat()}")

        return {
            "geometria_id": geometria_id,
            "epsg_utm": epsg_utm,
            "area_hectares": float(area_hectares),
            "perimetro_m": float(perimetro_m),
            "linhas": linhas,
            "texto": "\n".join(partes_txt),
            "gerado_em": now,
        }
