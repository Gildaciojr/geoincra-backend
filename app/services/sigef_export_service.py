from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass
from datetime import datetime
from io import StringIO
from math import atan2, degrees, floor, sqrt
from typing import List, Tuple

from fastapi import HTTPException
from pyproj import CRS, Transformer
from shapely.geometry import Polygon, shape

from app.services.geometria_service import GeometriaService


@dataclass(frozen=True)
class _PontoUTM:
    x: float
    y: float


class SigefExportService:
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
            geom = geom.buffer(0)

        if geom.is_empty or not geom.is_valid:
            raise HTTPException(status_code=400, detail="Geometria vazia ou inválida.")

        coords = list(geom.exterior.coords)
        if len(coords) < 4:
            raise HTTPException(
                status_code=400,
                detail="Polígono inválido (poucos vértices).",
            )

        return geom

    @staticmethod
    def _to_utm_points(
        geojson: str,
        epsg_origem: int,
    ) -> Tuple[int, List[_PontoUTM]]:
        analise = GeometriaService.analisar_referencial(
            geojson=geojson,
            epsg_origem=epsg_origem,
        )

        if analise["tipo_referencial"] != "GEOGRAFICA":
            raise HTTPException(
                status_code=400,
                detail=(
                    "Exportação SIGEF indisponível para geometria local/cartesiana. "
                    "É necessário georreferenciamento real."
                ),
            )

        if epsg_origem <= 0:
            raise HTTPException(status_code=400, detail="EPSG de origem inválido.")

        geom = SigefExportService._parse_polygon_geojson(geojson)

        lon = float(analise["centroid"]["x"])
        lat = float(analise["centroid"]["y"])

        epsg_utm = SigefExportService._utm_epsg_from_lonlat(lon, lat)

        crs_src = CRS.from_epsg(epsg_origem)
        crs_dst = CRS.from_epsg(epsg_utm)
        transformer = Transformer.from_crs(crs_src, crs_dst, always_xy=True)

        coords = list(geom.exterior.coords)
        if coords[0] != coords[-1]:
            coords.append(coords[0])

        pts: list[_PontoUTM] = []
        for x, y in coords:
            X, Y = transformer.transform(float(x), float(y))
            pts.append(_PontoUTM(x=float(X), y=float(Y)))

        if len(pts) < 4:
            raise HTTPException(
                status_code=400,
                detail="Polígono insuficiente para exportação SIGEF.",
            )

        return epsg_utm, pts

    @staticmethod
    def _dist_m(p1: _PontoUTM, p2: _PontoUTM) -> float:
        return float(sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2))

    @staticmethod
    def _azimute_deg(p1: _PontoUTM, p2: _PontoUTM) -> float:
        dx = p2.x - p1.x
        dy = p2.y - p1.y
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
        az = az % 360.0
        if 0.0 <= az < 90.0:
            ang = az
            return f"N {SigefExportService._deg_to_dms_str(ang)} E"
        if 90.0 <= az < 180.0:
            ang = 180.0 - az
            return f"S {SigefExportService._deg_to_dms_str(ang)} E"
        if 180.0 <= az < 270.0:
            ang = az - 180.0
            return f"S {SigefExportService._deg_to_dms_str(ang)} W"
        ang = 360.0 - az
        return f"N {SigefExportService._deg_to_dms_str(ang)} W"

    @staticmethod
    def gerar_csv_sigef(
        geojson: str,
        epsg_origem: int,
        prefixo_vertice: str = "V",
    ) -> Tuple[str, int, dict]:
        epsg_utm, pts = SigefExportService._to_utm_points(
            geojson=geojson,
            epsg_origem=epsg_origem,
        )

        n_segmentos = len(pts) - 1
        if n_segmentos < 3:
            raise HTTPException(
                status_code=400,
                detail="Polígono insuficiente para planilha SIGEF.",
            )

        rows: List[List[str]] = []
        header = [
            "ordem",
            "vertice_de",
            "vertice_ate",
            "x_utm_m",
            "y_utm_m",
            "azimute_graus",
            "rumo",
            "distancia_m",
            "epsg_utm",
        ]
        rows.append(header)

        for i in range(n_segmentos):
            p1 = pts[i]
            p2 = pts[i + 1]

            dist = SigefExportService._dist_m(p1, p2)
            az = SigefExportService._azimute_deg(p1, p2)
            rumo = SigefExportService._rumo_from_azimute(az)

            v_de = f"{prefixo_vertice}{i + 1}"
            v_ate = (
                f"{prefixo_vertice}{i + 2}"
                if i + 1 < n_segmentos
                else f"{prefixo_vertice}1"
            )

            rows.append(
                [
                    str(i + 1),
                    v_de,
                    v_ate,
                    f"{p1.x:.3f}",
                    f"{p1.y:.3f}",
                    f"{az:.6f}",
                    rumo,
                    f"{dist:.3f}",
                    str(epsg_utm),
                ]
            )

        buf = StringIO()
        writer = csv.writer(buf, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        for r in rows:
            writer.writerow(r)
        csv_str = buf.getvalue()

        metadata = {
            "formato": "CSV",
            "delimitador": ";",
            "epsg_origem": int(epsg_origem),
            "epsg_utm": int(epsg_utm),
            "prefixo_vertice": prefixo_vertice,
            "linhas": int(n_segmentos),
            "gerado_em_utc": datetime.utcnow().isoformat(),
            "tipo_referencial": "GEOGRAFICA",
        }

        return csv_str, epsg_utm, metadata

    @staticmethod
    def salvar_csv_em_disco(
        imovel_id: int,
        csv_str: str,
        base_dir: str = "app/uploads/imoveis",
    ) -> str:
        ts = int(datetime.utcnow().timestamp())
        folder = os.path.join(base_dir, str(imovel_id), "sigef")
        os.makedirs(folder, exist_ok=True)

        filename = f"planilha_sigef_{ts}.csv"
        path = os.path.join(folder, filename)

        with open(path, "w", encoding="utf-8", newline="") as f:
            f.write(csv_str)

        return path