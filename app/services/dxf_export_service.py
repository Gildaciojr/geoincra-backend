from __future__ import annotations

import json
import os
from datetime import datetime
from typing import List, Tuple

import ezdxf
from shapely.geometry import shape, Polygon


class DxfExportService:

    # =========================================================
    # GERAR DXF
    # =========================================================
    @staticmethod
    def gerar_dxf(geojson: str) -> str:
        geom = shape(json.loads(geojson))

        if geom.is_empty or not geom.is_valid:
            raise ValueError("Geometria inválida para DXF")

        if not isinstance(geom, Polygon):
            raise ValueError("Geometria deve ser POLYGON")

        coords: List[Tuple[float, float]] = list(geom.exterior.coords)

        if len(coords) < 4:
            raise ValueError("Polígono inválido para DXF")

        if coords[0] != coords[-1]:
            coords.append(coords[0])

        doc = ezdxf.new(dxfversion="R2010")
        msp = doc.modelspace()

        msp.add_lwpolyline(coords)

        # salvar em memória temporária (string path controlado depois)
        return doc

    # =========================================================
    # SALVAR DXF
    # =========================================================
    @staticmethod
    def salvar_dxf(
        imovel_id: int,
        doc,
        base_dir: str = "app/uploads/imoveis",
    ) -> str:

        ts = int(datetime.utcnow().timestamp())

        folder = os.path.join(base_dir, str(imovel_id), "cad")
        os.makedirs(folder, exist_ok=True)

        filename = f"perimetro_{ts}.dxf"
        path = os.path.join(folder, filename)

        doc.saveas(path)

        return path