from __future__ import annotations

import json
import os
from datetime import datetime
from shapely.geometry import shape


class CsvExportService:

    @staticmethod
    def gerar_csv(geojson: str):

        try:
            geom = shape(json.loads(geojson))
        except Exception as exc:
            raise ValueError("GeoJSON inválido para exportação CSV") from exc

        if geom.is_empty:
            raise ValueError("Geometria vazia para CSV")

        if not geom.is_valid:
            geom = geom.buffer(0)

        if geom.is_empty or not geom.is_valid:
            raise ValueError("Geometria inválida para CSV")

        coords = list(geom.exterior.coords)

        if len(coords) < 4:
            raise ValueError("Polígono inválido para CSV")

        if coords[0] != coords[-1]:
            coords.append(coords[0])

        lines = ["VERTICE,X,Y"]

        for i, (x, y) in enumerate(coords[:-1], start=1):
            lines.append(f"V{i},{float(x)},{float(y)}")

        return "\n".join(lines)

    @staticmethod
    def salvar_csv(
        imovel_id: int,
        csv: str,
        base_dir: str = "app/uploads/imoveis",
    ):

        ts = int(datetime.utcnow().timestamp())

        # ⚠️ NÃO alterei estrutura de pasta conforme sua regra
        folder = os.path.join(base_dir, str(imovel_id), "cad")

        os.makedirs(folder, exist_ok=True)

        filename = f"vertices_{ts}.csv"

        path = os.path.join(folder, filename)

        with open(path, "w") as f:
            f.write(csv)

        return path