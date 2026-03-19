from __future__ import annotations

import json
import os
from datetime import datetime
from typing import List, Tuple

from shapely.geometry import shape, Polygon


class TxtLispService:

    # =========================================================
    # GERAR TXT (FORMATO LISP/COORDENADAS)
    # =========================================================
    @staticmethod
    def gerar_txt(geojson: str) -> str:
        geom = shape(json.loads(geojson))

        if geom.is_empty or not geom.is_valid:
            raise ValueError("Geometria inválida para exportação TXT")

        if not isinstance(geom, Polygon):
            raise ValueError("Geometria deve ser POLYGON")

        coords: List[Tuple[float, float]] = list(geom.exterior.coords)

        if len(coords) < 4:
            raise ValueError("Polígono inválido para TXT")

        # garantir fechamento
        if coords[0] != coords[-1]:
            coords.append(coords[0])

        linhas: List[str] = []

        for i, (x, y) in enumerate(coords[:-1], start=1):
            linhas.append(f"V{i},{float(x)},{float(y)}")

        return "\n".join(linhas)

    # =========================================================
    # SALVAR TXT
    # =========================================================
    @staticmethod
    def salvar_txt(
        imovel_id: int,
        txt: str,
        base_dir: str = "app/uploads/imoveis",
    ) -> str:

        ts = int(datetime.utcnow().timestamp())

        folder = os.path.join(base_dir, str(imovel_id), "cad")
        os.makedirs(folder, exist_ok=True)

        filename = f"vertices_{ts}.txt"
        path = os.path.join(folder, filename)

        with open(path, "w", encoding="utf-8") as f:
            f.write(txt)

        return path