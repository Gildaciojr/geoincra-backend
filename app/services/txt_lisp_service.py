from __future__ import annotations

import os
import math
from datetime import datetime
from typing import List, Tuple

from shapely.geometry import Polygon
from app.services.geometria_service import GeometriaService


class TxtLispService:

    PRECISAO = 6  # padrão técnico coordenadas
    PRECISAO_DIST = 3  # metros
    PRECISAO_ANG = 2  # segundos

    # =========================================================
    # NORMALIZAÇÃO
    # =========================================================
    @staticmethod
    def _format_float(value: float) -> str:
        return f"{value:.{TxtLispService.PRECISAO}f}"

    @staticmethod
    def _format_dist(value: float) -> str:
        return f"{value:.{TxtLispService.PRECISAO_DIST}f}"

    # =========================================================
    # AZIMUTE → DMS
    # =========================================================
    @staticmethod
    def _deg_to_dms(az: float) -> Tuple[int, int, float]:
        d = int(az)
        m_float = (az - d) * 60
        m = int(m_float)
        s = (m_float - m) * 60
        return d, m, s

    @staticmethod
    def _format_dms(az: float) -> str:
        d, m, s = TxtLispService._deg_to_dms(az)
        return f"{d:02d}°{m:02d}'{s:0{2 + TxtLispService.PRECISAO_ANG + 1}.{TxtLispService.PRECISAO_ANG}f}\""

    # =========================================================
    # AZIMUTE E DISTÂNCIA
    # =========================================================
    @staticmethod
    def _calc_azimute(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]

        ang = math.degrees(math.atan2(dx, dy))
        if ang < 0:
            ang += 360.0

        return ang

    @staticmethod
    def _calc_distancia(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        return math.sqrt(dx * dx + dy * dy)

    # =========================================================
    # TXT ORIGINAL (MANTIDO)
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

        if coords[0] != coords[-1]:
            coords.append(coords[0])

        linhas: List[str] = []

        linhas.append("############################################")
        linhas.append("# ARQUIVO DE COORDENADAS - GEOINCRA")
        linhas.append(f"# GERADO EM: {datetime.utcnow().isoformat()}")
        linhas.append(f"# TOTAL VERTICES: {len(coords) - 1}")
        linhas.append("# FORMATO: VERTICE, X, Y")
        linhas.append("############################################")
        linhas.append("")

        for i, (x, y) in enumerate(coords[:-1], start=1):
            linhas.append(
                f"V{i},"
                f"{TxtLispService._format_float(float(x))},"
                f"{TxtLispService._format_float(float(y))}"
            )

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
    # 🔥 NOVO — PERÍMETRO TÉCNICO (ENGENHARIA)
    # =========================================================
    @staticmethod
    def gerar_txt_perimetro(geojson: str) -> str:
        try:
            geom: Polygon = GeometriaService._parse_polygon_geojson(geojson)
        except Exception as exc:
            raise ValueError("Geometria inválida para perímetro") from exc

        coords: List[Tuple[float, float]] = list(geom.exterior.coords)

        if len(coords) < 4:
            raise ValueError("Polígono inválido")

        if coords[0] != coords[-1]:
            coords.append(coords[0])

        linhas: List[str] = []

        # =========================================================
        # HEADER
        # =========================================================
        linhas.append("############################################")
        linhas.append("# PERIMETRO TECNICO - GEOINCRA")
        linhas.append(f"# GERADO EM: {datetime.utcnow().isoformat()}")
        linhas.append(f"# TOTAL SEGMENTOS: {len(coords) - 1}")
        linhas.append("# FORMATO: @distancia<azimute")
        linhas.append("############################################")
        linhas.append("")

        perimetro_total = 0.0

        # =========================================================
        # SEGMENTOS
        # =========================================================
        for i in range(len(coords) - 1):
            p1 = coords[i]
            p2 = coords[i + 1]

            distancia = TxtLispService._calc_distancia(p1, p2)
            azimute = TxtLispService._calc_azimute(p1, p2)

            perimetro_total += distancia

            linha = (
                f"L{i+1} "
                f"@{TxtLispService._format_dist(distancia)}"
                f"<{TxtLispService._format_dms(azimute)}"
            )

            linhas.append(linha)

        # =========================================================
        # RESUMO FINAL
        # =========================================================
        linhas.append("")
        linhas.append("############################################")
        linhas.append(f"# PERIMETRO TOTAL: {TxtLispService._format_dist(perimetro_total)} m")
        linhas.append("############################################")

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