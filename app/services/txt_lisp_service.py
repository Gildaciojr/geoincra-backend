from __future__ import annotations

import json
import os
from datetime import datetime
from typing import List, Tuple

from shapely.geometry import Polygon
from app.services.geometria_service import GeometriaService


class TxtLispService:

    PRECISAO = 6  # padrão técnico

    # =========================================================
    # NORMALIZAÇÃO
    # =========================================================
    @staticmethod
    def _format_float(value: float) -> str:
        return f"{value:.{TxtLispService.PRECISAO}f}"

    # =========================================================
    # GERAR TXT PROFISSIONAL
    # =========================================================
    @staticmethod
    def gerar_txt(geojson: str) -> str:
        try:
            geom: Polygon = GeometriaService._parse_polygon_geojson(geojson)
        except Exception as exc:
            raise ValueError("Geometria inválida para exportação TXT") from exc

        coords: List[Tuple[float, float]] = list(geom.exterior.coords)

        if len(coords) < 4:
            raise ValueError("Polígono inválido para TXT")

        # garantir fechamento
        if coords[0] != coords[-1]:
            coords.append(coords[0])

        linhas: List[str] = []

        # =========================================================
        # HEADER TÉCNICO
        # =========================================================
        linhas.append("############################################")
        linhas.append("# ARQUIVO DE COORDENADAS - GEOINCRA")
        linhas.append(f"# GERADO EM: {datetime.utcnow().isoformat()}")
        linhas.append(f"# TOTAL VERTICES: {len(coords) - 1}")
        linhas.append("# FORMATO: VERTICE, X, Y")
        linhas.append("############################################")
        linhas.append("")

        # =========================================================
        # VÉRTICES
        # =========================================================
        for i, (x, y) in enumerate(coords[:-1], start=1):
            linhas.append(
                f"V{i},"
                f"{TxtLispService._format_float(float(x))},"
                f"{TxtLispService._format_float(float(y))}"
            )

        # =========================================================
        # FECHAMENTO
        # =========================================================
        linhas.append("")
        linhas.append("# FECHAMENTO")
        x0, y0 = coords[0]

        linhas.append(
            f"V{len(coords)},"
            f"{TxtLispService._format_float(float(x0))},"
            f"{TxtLispService._format_float(float(y0))}"
        )

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

        filename = f"vertices_profissional_{ts}.txt"
        path = os.path.join(folder, filename)

        with open(path, "w", encoding="utf-8") as f:
            f.write(txt)

        return path