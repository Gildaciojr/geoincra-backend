# app/services/memorial_parser_service.py

from __future__ import annotations

import re
from math import sin, cos, radians
from shapely.geometry import Polygon


class MemorialParserService:
    """
    Parser de memorial descritivo capaz de interpretar:

    - Rumo quadrantal:
        Rumo N 45°00'00" E — Distância 120.50 m

    - Azimute direto:
        Azimute 01°22'35" — Distância 495.50 m

    Gera coordenadas relativas e retorna GeoJSON.
    """

    # ---------------------------------------------------------
    # UTILIDADES
    # ---------------------------------------------------------

    @staticmethod
    def _dms_para_decimal(g: float, m: float, s: float) -> float:
        return g + (m / 60) + (s / 3600)

    # ---------------------------------------------------------
    # RUMO -> AZIMUTE
    # ---------------------------------------------------------

    @staticmethod
    def _rumo_para_azimute(rumo: str) -> float:

        rumo = rumo.upper()

        match = re.search(
            r"([NS])\s*(\d+)[°º]\s*(\d+)'?\s*(\d+(?:\.\d+)?)?\"?\s*([EW])",
            rumo
        )

        if not match:
            raise ValueError(f"Rumo inválido: {rumo}")

        ns, g, m, s, ew = match.groups()

        g = float(g)
        m = float(m)
        s = float(s or 0)

        ang = MemorialParserService._dms_para_decimal(g, m, s)

        if ns == "N" and ew == "E":
            az = ang
        elif ns == "S" and ew == "E":
            az = 180 - ang
        elif ns == "S" and ew == "W":
            az = 180 + ang
        elif ns == "N" and ew == "W":
            az = 360 - ang
        else:
            raise ValueError("Rumo inválido")

        return az

    # ---------------------------------------------------------
    # AZIMUTE DIRETO
    # ---------------------------------------------------------

    @staticmethod
    def _azimute_dms_para_decimal(az_str: str) -> float:

        match = re.search(
            r"(\d+)[°º]\s*(\d+)'?\s*(\d+(?:\.\d+)?)?\"?",
            az_str
        )

        if not match:
            raise ValueError(f"Azimute inválido: {az_str}")

        g, m, s = match.groups()

        g = float(g)
        m = float(m)
        s = float(s or 0)

        return MemorialParserService._dms_para_decimal(g, m, s)

    # ---------------------------------------------------------
    # EXTRAÇÃO DE SEGMENTOS
    # ---------------------------------------------------------

    @staticmethod
    def extrair_segmentos(memorial_texto: str):

        segmentos = []

        # -----------------------------
        # RUMO + DISTANCIA
        # -----------------------------

        pattern_rumo = re.compile(
            r"Rumo\s*(.*?)\s*[—-]\s*Dist[aâ]ncia\s*(\d+(?:[.,]\d+)?)",
            re.IGNORECASE,
        )

        for rumo, distancia in pattern_rumo.findall(memorial_texto):

            distancia = float(distancia.replace(",", "."))

            az = MemorialParserService._rumo_para_azimute(rumo)

            segmentos.append({
                "tipo": "rumo",
                "rumo": rumo,
                "azimute": az,
                "distancia": distancia
            })

        # -----------------------------
        # AZIMUTE + DISTANCIA
        # -----------------------------

        pattern_az = re.compile(
            r"Azimute\s*(.*?)\s*[—-]\s*Dist[aâ]ncia\s*(\d+(?:[.,]\d+)?)",
            re.IGNORECASE,
        )

        for az_str, distancia in pattern_az.findall(memorial_texto):

            distancia = float(distancia.replace(",", "."))

            az = MemorialParserService._azimute_dms_para_decimal(az_str)

            segmentos.append({
                "tipo": "azimute",
                "azimute": az,
                "distancia": distancia
            })

        if not segmentos:
            raise ValueError("Nenhum segmento reconhecido no memorial")

        return segmentos

    # ---------------------------------------------------------
    # GEOMETRIA
    # ---------------------------------------------------------

    @staticmethod
    def gerar_geometria(memorial_texto: str):

        segmentos = MemorialParserService.extrair_segmentos(memorial_texto)

        x = 0.0
        y = 0.0

        coords = [(x, y)]

        for seg in segmentos:

            az = radians(seg["azimute"])

            dx = seg["distancia"] * sin(az)
            dy = seg["distancia"] * cos(az)

            x += dx
            y += dy

            coords.append((x, y))

        poly = Polygon(coords)

        if not poly.is_valid:
            raise ValueError("Geometria inválida gerada do memorial")

        return {
            "geojson": poly.__geo_interface__,
            "coords": coords,
            "segmentos": segmentos
        }