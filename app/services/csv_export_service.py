from __future__ import annotations

import json
import os
from datetime import datetime
from shapely.geometry import shape


class CsvExportService:

    @staticmethod
    def gerar_csv(geojson: str):

        geom = shape(json.loads(geojson))

        coords = list(geom.exterior.coords)

        lines = ["VERTICE,X,Y"]

        for i, (x, y) in enumerate(coords[:-1], start=1):
            lines.append(f"V{i},{x},{y}")

        return "\n".join(lines)

    @staticmethod
    def salvar_csv(
        imovel_id: int,
        csv: str,
        base_dir: str = "app/uploads/imoveis",
    ):

        ts = int(datetime.utcnow().timestamp())

        folder = os.path.join(base_dir, str(imovel_id), "cad")

        os.makedirs(folder, exist_ok=True)

        filename = f"vertices_{ts}.csv"

        path = os.path.join(folder, filename)

        with open(path, "w") as f:
            f.write(csv)

        return path