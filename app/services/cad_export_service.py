from __future__ import annotations

import json
import os
from datetime import datetime
from shapely.geometry import shape


class CadExportService:

    # =========================================================
    # GERAR SCRIPT AUTOCAD
    # =========================================================

    @staticmethod
    def gerar_scr(geojson: str):

        try:
            geom = shape(json.loads(geojson))
        except Exception as exc:
            raise ValueError("GeoJSON inválido para exportação CAD") from exc

        if geom.is_empty:
            raise ValueError("Geometria vazia para exportação CAD")

        if not geom.is_valid:
            geom = geom.buffer(0)

        if geom.is_empty or not geom.is_valid:
            raise ValueError("Geometria inválida para exportação CAD")

        coords = list(geom.exterior.coords)

        if len(coords) < 4:
            raise ValueError("Polígono inválido para CAD")

        # garantir fechamento
        if coords[0] != coords[-1]:
            coords.append(coords[0])

        lines = []
        lines.append("PLINE")

        for x, y in coords:
            lines.append(f"{float(x)},{float(y)}")

        lines.append("C")

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

        with open(path, "w") as f:
            f.write(scr)

        return path