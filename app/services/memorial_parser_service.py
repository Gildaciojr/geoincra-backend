# app/services/memorial_parser_service.py

import re
from math import sin, cos, radians
from shapely.geometry import Polygon


class MemorialParserService:

    @staticmethod
    def _rumo_para_azimute(rumo: str) -> float:
        """
        Converte rumo quadrantal para azimute.
        Ex: N 45°00'00" E
        """

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

        ang = g + (m / 60) + (s / 3600)

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

    @staticmethod
    def extrair_segmentos(memorial_texto: str):
        """
        Extrai segmentos do memorial.
        """

        pattern = re.compile(
            r"Rumo\s*(.*?)\s*—\s*Dist[aâ]ncia\s*(\d+(?:\.\d+)?)",
            re.IGNORECASE,
        )

        segmentos = []

        for rumo, distancia in pattern.findall(memorial_texto):

            az = MemorialParserService._rumo_para_azimute(rumo)

            segmentos.append({
                "rumo": rumo,
                "distancia": float(distancia),
                "azimute": az
            })

        if not segmentos:
            raise ValueError("Nenhum segmento encontrado no memorial")

        return segmentos

    @staticmethod
    def gerar_geometria(memorial_texto: str):

        segmentos = MemorialParserService.extrair_segmentos(memorial_texto)

        x = 0
        y = 0

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
            "coords": coords
        }