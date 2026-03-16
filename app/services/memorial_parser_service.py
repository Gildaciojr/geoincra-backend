# app/services/memorial_parser_service.py

from __future__ import annotations

import re
from math import cos, radians, sin
from typing import Any

from shapely.geometry import Polygon


class MemorialParserService:
    """
    Parser de memorial descritivo com suporte a:

    - rumo quadrantal
      Ex.: N 45°00'00" E

    - azimute direto
      Ex.: 01°22'35"

    - linhas com distância em ponto ou vírgula

    Retorna geometria relativa em GeoJSON.
    """

    @staticmethod
    def _dms_para_decimal(
        graus: float,
        minutos: float,
        segundos: float,
    ) -> float:
        return graus + (minutos / 60) + (segundos / 3600)

    @staticmethod
    def _rumo_para_azimute(rumo: str) -> float:
        rumo_normalizado = " ".join(rumo.upper().strip().split())

        match = re.search(
            r"([NS])\s*(\d+)[°º]\s*(\d+)'?\s*(\d+(?:\.\d+)?)?\"?\s*([EW])",
            rumo_normalizado,
        )

        if not match:
            raise ValueError(f"Rumo inválido: {rumo}")

        ns, g, m, s, ew = match.groups()

        graus = float(g)
        minutos = float(m)
        segundos = float(s or 0)

        angulo = MemorialParserService._dms_para_decimal(
            graus,
            minutos,
            segundos,
        )

        if ns == "N" and ew == "E":
            return angulo
        if ns == "S" and ew == "E":
            return 180 - angulo
        if ns == "S" and ew == "W":
            return 180 + angulo
        if ns == "N" and ew == "W":
            return 360 - angulo

        raise ValueError(f"Rumo inválido: {rumo}")

    @staticmethod
    def _azimute_dms_para_decimal(azimute: str) -> float:
        azimute_normalizado = " ".join(azimute.strip().split())

        match = re.search(
            r"(\d+)[°º]\s*(\d+)'?\s*(\d+(?:\.\d+)?)?\"?",
            azimute_normalizado,
        )

        if not match:
            raise ValueError(f"Azimute inválido: {azimute}")

        g, m, s = match.groups()

        return MemorialParserService._dms_para_decimal(
            float(g),
            float(m),
            float(s or 0),
        )

    @staticmethod
    def _parse_distancia(valor: Any) -> float:
        if isinstance(valor, (int, float)):
            return float(valor)

        texto = str(valor).strip()

        # remove milhar e padroniza decimal
        texto = texto.replace(".", "").replace(",", ".")

        return float(texto)

    @staticmethod
    def extrair_segmentos(memorial_texto: str) -> list[dict[str, Any]]:
        """
        Suporta padrões como:

        - Rumo N 45°00'00" E — Distância 120,50
        - Azimute 01°22'35" — Distância 495,50
        - com azimute de 01°22'35", na distância de 495,50 metros
        """
        if not memorial_texto or not memorial_texto.strip():
            raise ValueError("Memorial vazio")

        segmentos: list[dict[str, Any]] = []

        # -----------------------------------------------------
        # PADRÃO 1: RUMO + DISTÂNCIA
        # -----------------------------------------------------

        pattern_rumo = re.compile(
            r"Rumo\s*(.*?)\s*[—-]?\s*Dist[aâ]ncia\s*(\d+(?:[.,]\d+)?)",
            re.IGNORECASE,
        )

        for rumo, distancia in pattern_rumo.findall(memorial_texto):
            az = MemorialParserService._rumo_para_azimute(rumo)
            dist = MemorialParserService._parse_distancia(distancia)

            segmentos.append(
                {
                    "tipo": "rumo",
                    "rumo": rumo.strip(),
                    "azimute": az,
                    "distancia": dist,
                }
            )

        # -----------------------------------------------------
        # PADRÃO 2: AZIMUTE + DISTÂNCIA
        # -----------------------------------------------------

        pattern_azimute_livre = re.compile(
            r"azimute\s*(?:de)?\s*(\d+[°º]\s*\d+'?\s*\d*(?:\.\d+)?\"?)"
            r".{0,40}?"
            r"dist[âa]ncia\s*(?:de)?\s*(\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+(?:[.,]\d+)?)",
            re.IGNORECASE | re.DOTALL,
        )

        for az_str, distancia in pattern_azimute_livre.findall(memorial_texto):
            az = MemorialParserService._azimute_dms_para_decimal(az_str)
            dist = MemorialParserService._parse_distancia(distancia)

            segmentos.append(
                {
                    "tipo": "azimute",
                    "rumo": az_str.strip(),
                    "azimute": az,
                    "distancia": dist,
                }
            )

        if not segmentos:
            raise ValueError("Nenhum segmento encontrado no memorial")

        return segmentos

    @staticmethod
    def gerar_geometria(memorial_texto: str) -> dict[str, Any]:
        segmentos = MemorialParserService.extrair_segmentos(memorial_texto)

        x = 0.0
        y = 0.0
        coords: list[tuple[float, float]] = [(x, y)]

        for seg in segmentos:
            az = radians(float(seg["azimute"]))

            dx = float(seg["distancia"]) * sin(az)
            dy = float(seg["distancia"]) * cos(az)

            x += dx
            y += dy

            coords.append((x, y))

        if len(coords) < 4:
            raise ValueError("Quantidade insuficiente de vértices para polígono")

        if coords[0] != coords[-1]:
            coords.append(coords[0])

        poly = Polygon(coords)

        if poly.is_empty or not poly.is_valid:
            raise ValueError("Geometria inválida gerada do memorial")

        return {
            "geojson": poly.__geo_interface__,
            "coords": coords,
            "segmentos": segmentos,
        }