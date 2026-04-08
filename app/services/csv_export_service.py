from __future__ import annotations

import json
import math
import os
from datetime import datetime

from shapely.geometry import Polygon
from app.services.geometria_service import GeometriaService


class CsvExportService:

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
    def _sanear_coords(coords):
        coords_validos = []

        for x, y in coords:
            xf = CsvExportService._safe_float(x)
            yf = CsvExportService._safe_float(y)

            if math.isnan(xf) or math.isnan(yf) or math.isinf(xf) or math.isinf(yf):
                continue

            coords_validos.append((xf, yf))

        return coords_validos

    @staticmethod
    def gerar_csv(geojson: str):

        try: 
            geom: Polygon = GeometriaService._parse_polygon_geojson(geojson)
        except Exception as exc:
            raise ValueError("GeoJSON inválido para exportação CSV") from exc

        coords = list(geom.exterior.coords)
        coords = CsvExportService._sanear_coords(coords)

        if len(coords) < 4:
            raise ValueError("Polígono inválido para CSV")

        if coords[0] != coords[-1]:
            coords.append(coords[0])

        lines = ["VERTICE,ORDEM,X,Y"]

        for i, (x, y) in enumerate(coords[:-1], start=1):
            lines.append(f"V{i},{i},{x:.6f},{y:.6f}")

        # linha de fechamento explícita
        x0, y0 = coords[0]
        lines.append(f"V1_FECHAMENTO,{len(coords)},{x0:.6f},{y0:.6f}")

        return "\n".join(lines)

    @staticmethod
    def salvar_csv(
        imovel_id: int,
        csv: str,
        base_dir: str = "app/uploads/imoveis",
    ):

        ts = int(datetime.utcnow().timestamp())

        # ⚠️ mantido conforme sua regra
        folder = os.path.join(base_dir, str(imovel_id), "cad")

        os.makedirs(folder, exist_ok=True)

        filename = f"vertices_{ts}.csv"

        path = os.path.join(folder, filename)

        with open(path, "w", encoding="utf-8") as f:
            f.write(csv)

        return path