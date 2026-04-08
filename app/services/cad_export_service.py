from __future__ import annotations

import json
import math
import os
from datetime import datetime
from shapely.geometry import Polygon
from app.services.geometria_service import GeometriaService


class CadExportService:

    # =========================================================
    # HELPERS
    # =========================================================

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
            xf = CadExportService._safe_float(x)
            yf = CadExportService._safe_float(y)

            if math.isnan(xf) or math.isnan(yf) or math.isinf(xf) or math.isinf(yf):
                continue

            coords_validos.append((xf, yf))

        return coords_validos

    # =========================================================
    # GERAR SCRIPT AUTOCAD
    # =========================================================

    @staticmethod
    def gerar_scr(geojson: str):

        try:
            geom: Polygon = GeometriaService._parse_polygon_geojson(geojson)
        except Exception as exc:
            raise ValueError("GeoJSON inválido para exportação CAD") from exc


        coords = list(geom.exterior.coords)
        coords = CadExportService._sanear_coords(coords)

        if len(coords) < 4:
            raise ValueError("Polígono inválido para CAD")

        if coords[0] != coords[-1]:
            coords.append(coords[0])

        lines = []

        # =========================
        # CONFIGURAÇÕES INICIAIS
        # =========================
        lines.append("._UNDO _BEGIN")
        lines.append("._INSUNITS 6")  # metros
        lines.append("._LAYER M PERIMETRO C 2 PERIMETRO")
        lines.append("._LAYER S PERIMETRO")

        # =========================
        # DESENHAR POLILINHA
        # =========================
        lines.append("._PLINE")

        for x, y in coords:
            lines.append(f"{x:.6f},{y:.6f}")

        lines.append("C")

        # =========================
        # MARCAR VÉRTICES
        # =========================
        for i, (x, y) in enumerate(coords[:-1], start=1):
            lines.append("._POINT")
            lines.append(f"{x:.6f},{y:.6f}")

            # texto identificador
            lines.append("._TEXT")
            lines.append(f"{x:.6f},{y:.6f}")
            lines.append("2")  # altura do texto
            lines.append("0")  # rotação
            lines.append(f"V{i}")

        # =========================
        # FINALIZAÇÃO
        # =========================
        lines.append("._UNDO _END")

        return "\n".join(lines)

    # =========================================================
    # SALVAR SCRIPT
    # =========================================================

    @staticmethod
    def salvar_scr(
        imovel_id: int,
        scr: str,
        base_dir: str = "app/uploads/imoveis",
    ):

        ts = int(datetime.utcnow().timestamp())

        folder = os.path.join(base_dir, str(imovel_id), "cad")

        os.makedirs(folder, exist_ok=True)

        filename = f"perimetro_{ts}.scr"

        path = os.path.join(folder, filename)

        with open(path, "w", encoding="utf-8") as f:
            f.write(scr)

        return path