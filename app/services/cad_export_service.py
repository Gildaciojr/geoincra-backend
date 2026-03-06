from __future__ import annotations

import json
import os
from datetime import datetime
from shapely.geometry import shape


class CadExportService:

    @staticmethod
    def gerar_scr(geojson: str):

        geom = shape(json.loads(geojson))

        coords = list(geom.exterior.coords)

        lines = []

        lines.append("PLINE")

        for x, y in coords:
            lines.append(f"{x},{y}")

        lines.append("C")

        return "\n".join(lines)

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