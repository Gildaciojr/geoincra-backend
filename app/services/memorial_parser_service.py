# app/services/memorial_parser_service.py

from __future__ import annotations

import re
from math import cos, radians, sin, sqrt
from typing import Any

from shapely.geometry import Polygon


class MemorialParserService:

    FECHAMENTO_TOLERANCIA_METROS = 2.0

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
        texto = texto.replace(".", "").replace(",", ".")

        try:
            dist = float(texto)
        except Exception:
            raise ValueError(f"Distância inválida: {valor}")

        if dist <= 0:
            raise ValueError("Distância deve ser positiva")

        return dist

    @staticmethod
    def _distancia_entre_pontos(
        p1: tuple[float, float],
        p2: tuple[float, float],
    ) -> float:
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        return sqrt((dx * dx) + (dy * dy))

    @staticmethod
    def _fechar_anel(coords: list[tuple[float, float]]) -> list[tuple[float, float]]:
        if len(coords) < 3:
            raise ValueError("Quantidade insuficiente de vértices para polígono")

        primeiro = coords[0]
        ultimo = coords[-1]

        distancia_fechamento = MemorialParserService._distancia_entre_pontos(
            primeiro,
            ultimo,
        )

        if distancia_fechamento <= MemorialParserService.FECHAMENTO_TOLERANCIA_METROS:
            coords[-1] = primeiro
            return coords

        if primeiro != ultimo:
            coords.append(primeiro)

        return coords

    # 🔥 CORREÇÃO CRÍTICA: AGORA DENTRO DA CLASSE
    @staticmethod
    def extrair_segmentos(memorial_texto: str) -> list[dict[str, Any]]:
        if not memorial_texto or not memorial_texto.strip():
            raise ValueError("Memorial vazio")

        segmentos: list[dict[str, Any]] = []

        pattern_rumo = re.compile(
            r"Rumo\s*(.*?)\s*[—\-]?\s*Dist[aâ]ncia\s*(\d+(?:[.,]\d+)?)",
            re.IGNORECASE,
        )

        for rumo, distancia in pattern_rumo.findall(memorial_texto):
            try:
                az = MemorialParserService._rumo_para_azimute(rumo)
                dist = MemorialParserService._parse_distancia(distancia)

                if dist <= 0:
                    continue

                segmentos.append(
                    {
                        "tipo": "rumo",
                        "rumo": rumo.strip(),
                        "azimute": az,
                        "distancia": dist,
                    }
                )
            except Exception:
                continue

        pattern_azimute_livre = re.compile(
            r"azimute\s*(?:de)?\s*(\d+[°º]\s*\d+'?\s*\d*(?:\.\d+)?\"?)"
            r".{0,40}?"
            r"dist[âa]ncia\s*(?:de)?\s*(\d+(?:[.,]\d+)?)",
            re.IGNORECASE | re.DOTALL,
        )

        for az_str, distancia in pattern_azimute_livre.findall(memorial_texto):
            try:
                az = MemorialParserService._azimute_dms_para_decimal(az_str)
                dist = MemorialParserService._parse_distancia(distancia)

                if dist <= 0:
                    continue

                segmentos.append(
                    {
                        "tipo": "azimute",
                        "rumo": az_str.strip(),
                        "azimute": az,
                        "distancia": dist,
                    }
                )
            except Exception:
                continue

        if not segmentos:
            raise ValueError("Nenhum segmento válido encontrado no memorial")

        return segmentos

    @staticmethod
    def gerar_geometria(memorial_texto: str) -> dict[str, Any]:
        segmentos = MemorialParserService.extrair_segmentos(memorial_texto)

        x: float = 0.0
        y: float = 0.0

        coords: list[tuple[float, float]] = [(x, y)]

        for seg in segmentos:
            azimute = seg.get("azimute")
            distancia = seg.get("distancia")

            if azimute is None or distancia is None:
                raise ValueError("Segmento inválido: azimute ou distância ausente")

            az = radians(float(azimute))
            dist = float(distancia)

            dx = dist * sin(az)
            dy = dist * cos(az)

            x += dx
            y += dy

            coords.append((x, y))

        coords = MemorialParserService._fechar_anel(coords)

        polygon = Polygon(coords)

        if polygon.is_empty:
            raise ValueError("Geometria vazia gerada do memorial")

        if not polygon.is_valid:
            polygon = polygon.buffer(0)

        if polygon.is_empty or not polygon.is_valid:
            raise ValueError("Geometria inválida gerada do memorial")

        return {
            "geojson": polygon.__geo_interface__,
            "coords": coords,
            "segmentos": segmentos,
        }