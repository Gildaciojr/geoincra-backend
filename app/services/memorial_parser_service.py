# app/services/memorial_parser_service.py

from __future__ import annotations

import re
from math import cos, radians, sin, sqrt
from typing import Any

from shapely.geometry import Polygon


class MemorialParserService:

    FECHAMENTO_TOLERANCIA_METROS = 2.0
    DISTANCIA_MINIMA_METROS = 0.01

    @staticmethod
    def _normalizar_espacos(texto: str) -> str:
        return " ".join(str(texto or "").strip().split())

    @staticmethod
    def _normalizar_texto_base(texto: str) -> str:
        return (
            MemorialParserService._normalizar_espacos(texto)
            .replace("–", "-")
            .replace("—", "-")
            .replace("“", '"')
            .replace("”", '"')
            .replace("´", "'")
            .replace("`", "'")
        )

    @staticmethod
    def _dms_para_decimal(
        graus: float,
        minutos: float,
        segundos: float,
    ) -> float:
        return graus + (minutos / 60) + (segundos / 3600)

    @staticmethod
    def _rumo_para_azimute(rumo: str) -> float:
        rumo_normalizado = MemorialParserService._normalizar_texto_base(rumo).upper()

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

        if angulo < 0 or angulo > 90:
            raise ValueError(f"Rumo inválido fora do quadrante: {rumo}")

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
        azimute_normalizado = MemorialParserService._normalizar_texto_base(azimute)

        match = re.search(
            r"(\d+)[°º]\s*(\d+)'?\s*(\d+(?:\.\d+)?)?\"?",
            azimute_normalizado,
        )

        if not match:
            raise ValueError(f"Azimute inválido: {azimute}")

        g, m, s = match.groups()

        decimal = MemorialParserService._dms_para_decimal(
            float(g),
            float(m),
            float(s or 0),
        )

        if decimal < 0 or decimal > 360:
            raise ValueError(f"Azimute fora do intervalo válido: {azimute}")

        return decimal

    @staticmethod
    def _azimute_decimal_para_float(azimute: str) -> float:
        texto = MemorialParserService._normalizar_texto_base(azimute)
        texto = texto.replace(",", ".")

        try:
            valor = float(texto)
        except Exception:
            raise ValueError(f"Azimute decimal inválido: {azimute}")

        if valor < 0 or valor > 360:
            raise ValueError(f"Azimute decimal fora do intervalo válido: {azimute}")

        return valor

    @staticmethod
    def _parse_azimute_ou_rumo(valor: str) -> float:
        texto = MemorialParserService._normalizar_texto_base(valor)

        # primeiro tenta rumo quadrantal
        if re.search(r"^[NS]\s*.+\s*[EW]$", texto.upper()):
            return MemorialParserService._rumo_para_azimute(texto)

        # depois tenta DMS
        if re.search(r"\d+[°º]\s*\d+", texto):
            return MemorialParserService._azimute_dms_para_decimal(texto)

        # por último tenta decimal puro
        return MemorialParserService._azimute_decimal_para_float(texto)

    @staticmethod
    def _parse_distancia(valor: Any) -> float:
        if isinstance(valor, (int, float)):
            dist = float(valor)
            if dist <= 0:
                raise ValueError("Distância deve ser positiva")
            return dist

        texto = MemorialParserService._normalizar_texto_base(str(valor))

        if not texto:
            raise ValueError("Distância vazia")

        texto = texto.lower()
        texto = texto.replace("metros", "")
        texto = texto.replace("metro", "")
        texto = texto.replace("m.", "")
        texto = texto.replace("m", "")
        texto = texto.strip()

        if "," in texto and "." in texto:
            if texto.rfind(",") > texto.rfind("."):
                texto = texto.replace(".", "").replace(",", ".")
            else:
                texto = texto.replace(",", "")
        else:
            if "," in texto:
                texto = texto.replace(".", "").replace(",", ".")
            else:
                texto = texto.replace(",", "")

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
    def _fechar_anel(coords: list[tuple[float, float]]) -> tuple[list[tuple[float, float]], float]:
        if len(coords) < 3:
            raise ValueError("Quantidade insuficiente de vértices para polígono")

        primeiro = coords[0]
        ultimo = coords[-1]

        erro_fechamento = MemorialParserService._distancia_entre_pontos(
            primeiro,
            ultimo,
        )

        if erro_fechamento <= MemorialParserService.FECHAMENTO_TOLERANCIA_METROS:
            coords[-1] = primeiro
            return coords, erro_fechamento

        raise ValueError(
            f"Erro de fechamento do polígono: {erro_fechamento:.3f} m "
            f"(acima da tolerância de {MemorialParserService.FECHAMENTO_TOLERANCIA_METROS} m)"
        )

    @staticmethod
    def _adicionar_segmento(
        segmentos: list[dict[str, Any]],
        tipo: str,
        rumo_original: str,
        azimute: float,
        distancia: float,
        ordem: int | None = None,
        vertice_inicial: str | None = None,
        vertice_final: str | None = None,
    ) -> None:
        if distancia <= 0:
            return

        segmento: dict[str, Any] = {
            "tipo": tipo,
            "rumo": MemorialParserService._normalizar_texto_base(rumo_original),
            "azimute": float(azimute),
            "distancia": float(distancia),
        }

        if ordem is not None:
            segmento["ordem"] = ordem

        if vertice_inicial:
            segmento["vertice_inicial"] = MemorialParserService._normalizar_texto_base(
                vertice_inicial
            ).upper()

        if vertice_final:
            segmento["vertice_final"] = MemorialParserService._normalizar_texto_base(
                vertice_final
            ).upper()

        segmentos.append(segmento)

    @staticmethod
    def _deduplicar_segmentos(segmentos: list[dict[str, Any]]) -> list[dict[str, Any]]:
        segmentos_unicos: list[dict[str, Any]] = []
        vistos: set[tuple[str, float, float]] = set()

        for seg in segmentos:
            chave = (
                str(seg.get("rumo", "")).strip().upper(),
                round(float(seg.get("azimute", 0.0)), 8),
                round(float(seg.get("distancia", 0.0)), 8),
            )

            if chave in vistos:
                continue

            vistos.add(chave)
            segmentos_unicos.append(seg)

        try:
            segmentos_unicos.sort(
                key=lambda x: (
                    0 if x.get("ordem") is not None else 1,
                    x.get("ordem") if x.get("ordem") is not None else 999999,
                )
            )
        except Exception:
            pass

        return segmentos_unicos

    @staticmethod
    def extrair_segmentos(memorial_texto: str) -> list[dict[str, Any]]:
        if not memorial_texto or not memorial_texto.strip():
            raise ValueError("Memorial vazio")

        texto = MemorialParserService._normalizar_texto_base(memorial_texto)
        segmentos: list[dict[str, Any]] = []

        # =========================================================
        # PADRÃO 1: "Rumo X Distância Y"
        # =========================================================
        pattern_rumo = re.compile(
            r"Rumo\s*(.*?)\s*[—\-]?\s*Dist[aâ]ncia\s*(\d+(?:[.,]\d+)?)",
            re.IGNORECASE,
        )

        for rumo, distancia in pattern_rumo.findall(texto):
            try:
                az = MemorialParserService._rumo_para_azimute(rumo)
                dist = MemorialParserService._parse_distancia(distancia)

                MemorialParserService._adicionar_segmento(
                    segmentos=segmentos,
                    tipo="rumo",
                    rumo_original=rumo,
                    azimute=az,
                    distancia=dist,
                )
            except Exception:
                continue

        # =========================================================
        # PADRÃO 2: "azimute X distância Y"
        # =========================================================
        pattern_azimute_livre = re.compile(
            r"azimute\s*(?:de)?\s*(\d+[°º]\s*\d+'?\s*\d*(?:\.\d+)?\"?)"
            r".{0,40}?"
            r"dist[âa]ncia\s*(?:de)?\s*(\d+(?:[.,]\d+)?)",
            re.IGNORECASE | re.DOTALL,
        )

        for az_str, distancia in pattern_azimute_livre.findall(texto):
            try:
                az = MemorialParserService._azimute_dms_para_decimal(az_str)
                dist = MemorialParserService._parse_distancia(distancia)

                MemorialParserService._adicionar_segmento(
                    segmentos=segmentos,
                    tipo="azimute",
                    rumo_original=az_str,
                    azimute=az,
                    distancia=dist,
                )
            except Exception:
                continue

        # =========================================================
        # PADRÃO 3: TEXTO REAL DE CARTÓRIO
        # =========================================================
        pattern_cartorio = re.compile(
            r"azimute\s*de\s*(\d+[°º]\s*\d+'?\s*\d*(?:\.\d+)?\"?)"
            r".{0,80}?"
            r"dist[âa]ncia\s*de\s*(\d+(?:[.,]\d+)?)",
            re.IGNORECASE | re.DOTALL,
        )

        for az_str, distancia in pattern_cartorio.findall(texto):
            try:
                az = MemorialParserService._azimute_dms_para_decimal(az_str)
                dist = MemorialParserService._parse_distancia(distancia)

                MemorialParserService._adicionar_segmento(
                    segmentos=segmentos,
                    tipo="cartorio",
                    rumo_original=az_str,
                    azimute=az,
                    distancia=dist,
                )
            except Exception:
                continue

        # =========================================================
        # PADRÃO 4: VARIAÇÃO COM "na distância de"
        # =========================================================
        pattern_cartorio_na_distancia = re.compile(
            r"azimute\s*de\s*(\d+[°º]\s*\d+'?\s*\d*(?:\.\d+)?\"?)"
            r".{0,100}?"
            r"na\s+dist[âa]ncia\s*de\s*(\d+(?:[.,]\d+)?)",
            re.IGNORECASE | re.DOTALL,
        )

        for az_str, distancia in pattern_cartorio_na_distancia.findall(texto):
            try:
                az = MemorialParserService._azimute_dms_para_decimal(az_str)
                dist = MemorialParserService._parse_distancia(distancia)

                MemorialParserService._adicionar_segmento(
                    segmentos=segmentos,
                    tipo="cartorio_na_distancia",
                    rumo_original=az_str,
                    azimute=az,
                    distancia=dist,
                )
            except Exception:
                continue

        # =========================================================
        # PADRÃO 5: VARIAÇÃO COM "metros" EXPLÍCITO
        # =========================================================
        pattern_cartorio_metros = re.compile(
            r"azimute\s*de\s*(\d+[°º]\s*\d+'?\s*\d*(?:\.\d+)?\"?)"
            r".{0,120}?"
            r"dist[âa]ncia\s*de\s*(\d+(?:[.,]\d+)?)\s*metros?",
            re.IGNORECASE | re.DOTALL,
        )

        for az_str, distancia in pattern_cartorio_metros.findall(texto):
            try:
                az = MemorialParserService._azimute_dms_para_decimal(az_str)
                dist = MemorialParserService._parse_distancia(distancia)

                MemorialParserService._adicionar_segmento(
                    segmentos=segmentos,
                    tipo="cartorio_metros",
                    rumo_original=az_str,
                    azimute=az,
                    distancia=dist,
                )
            except Exception:
                continue

        # =========================================================
        # PADRÃO 6: AZIMUTE DECIMAL + DISTÂNCIA
        # Ex.: "azimute 123.456789 distância 495,50"
        # =========================================================
        pattern_azimute_decimal = re.compile(
            r"azimute\s*(?:de)?\s*(\d+(?:[.,]\d+)?)"
            r".{0,50}?"
            r"dist[âa]ncia\s*(?:de)?\s*(\d+(?:[.,]\d+)?)",
            re.IGNORECASE | re.DOTALL,
        )

        for az_str, distancia in pattern_azimute_decimal.findall(texto):
            try:
                az = MemorialParserService._azimute_decimal_para_float(az_str)
                dist = MemorialParserService._parse_distancia(distancia)

                MemorialParserService._adicionar_segmento(
                    segmentos=segmentos,
                    tipo="azimute_decimal",
                    rumo_original=az_str,
                    azimute=az,
                    distancia=dist,
                )
            except Exception:
                continue

        # =========================================================
        # PADRÃO 7: RUMO + DISTÂNCIA + MARCOS/VÉRTICES
        # Ex.: "do vértice V01 ao vértice V02 com rumo N 10°00'00" E e distância 100,00"
        # =========================================================
        pattern_vertices_rumo = re.compile(
            r"(?:v[eé]rtice|marco)\s*([A-Z0-9.\-_/]+)"
            r".{0,40}?"
            r"(?:ao|até|ate)\s*(?:v[eé]rtice|marco)?\s*([A-Z0-9.\-_/]+)"
            r".{0,60}?"
            r"rumo\s*(.*?)\s*"
            r".{0,40}?"
            r"dist[âa]ncia\s*(?:de)?\s*(\d+(?:[.,]\d+)?)",
            re.IGNORECASE | re.DOTALL,
        )

        ordem_local = 1
        for v1, v2, rumo, distancia in pattern_vertices_rumo.findall(texto):
            try:
                az = MemorialParserService._rumo_para_azimute(rumo)
                dist = MemorialParserService._parse_distancia(distancia)

                MemorialParserService._adicionar_segmento(
                    segmentos=segmentos,
                    tipo="vertices_rumo",
                    rumo_original=rumo,
                    azimute=az,
                    distancia=dist,
                    ordem=ordem_local,
                    vertice_inicial=v1,
                    vertice_final=v2,
                )
                ordem_local += 1
            except Exception:
                continue

        # =========================================================
        # PADRÃO 8: MARCOS/VÉRTICES + AZIMUTE + DISTÂNCIA
        # =========================================================
        pattern_vertices_azimute = re.compile(
            r"(?:v[eé]rtice|marco)\s*([A-Z0-9.\-_/]+)"
            r".{0,40}?"
            r"(?:ao|até|ate)\s*(?:v[eé]rtice|marco)?\s*([A-Z0-9.\-_/]+)"
            r".{0,80}?"
            r"azimute\s*(?:de)?\s*(\d+[°º]\s*\d+'?\s*\d*(?:\.\d+)?\"?|\d+(?:[.,]\d+)?)"
            r".{0,60}?"
            r"dist[âa]ncia\s*(?:de)?\s*(\d+(?:[.,]\d+)?)",
            re.IGNORECASE | re.DOTALL,
        )

        ordem_local = 1
        for v1, v2, azimute_raw, distancia in pattern_vertices_azimute.findall(texto):
            try:
                az = MemorialParserService._parse_azimute_ou_rumo(azimute_raw)
                dist = MemorialParserService._parse_distancia(distancia)

                MemorialParserService._adicionar_segmento(
                    segmentos=segmentos,
                    tipo="vertices_azimute",
                    rumo_original=azimute_raw,
                    azimute=az,
                    distancia=dist,
                    ordem=ordem_local,
                    vertice_inicial=v1,
                    vertice_final=v2,
                )
                ordem_local += 1
            except Exception:
                continue

        segmentos_unicos = MemorialParserService._deduplicar_segmentos(segmentos)

        if not segmentos_unicos:
            return []

        return segmentos_unicos

    @staticmethod
    def gerar_geometria(memorial_texto: str) -> dict[str, Any]:
        segmentos = MemorialParserService.extrair_segmentos(memorial_texto)

        if not segmentos:
            raise ValueError("Não foi possível gerar geometria: memorial sem segmentos válidos")

        x: float = 0.0
        y: float = 0.0

        coords: list[tuple[float, float]] = [(x, y)]

        distancias_calculadas: list[float] = []
        azimutes_calculados: list[float] = []

        for idx, seg in enumerate(segmentos, start=1):
            azimute = seg.get("azimute")
            distancia = seg.get("distancia")

            if azimute is None or distancia is None:
                raise ValueError(f"Segmento inválido na posição {idx}: azimute ou distância ausente")

            az = radians(float(azimute))
            dist = float(distancia)

            if dist <= 0:
                raise ValueError(f"Segmento inválido na posição {idx}: distância não positiva")

            if dist < MemorialParserService.DISTANCIA_MINIMA_METROS:
                raise ValueError(
                    f"Segmento inválido na posição {idx}: distância muito pequena ({dist})"
                )

            dx = dist * sin(az)
            dy = dist * cos(az)

            x += dx
            y += dy

            coords.append((x, y))
            distancias_calculadas.append(dist)
            azimutes_calculados.append(float(seg.get("azimute")))

        if len(coords) < 4:
            raise ValueError("Geometria inválida: número insuficiente de vértices")

        for i in range(len(coords) - 1):
            dx = coords[i + 1][0] - coords[i][0]
            dy = coords[i + 1][1] - coords[i][1]
            dist = sqrt(dx * dx + dy * dy)

            if dist < MemorialParserService.DISTANCIA_MINIMA_METROS:
                raise ValueError(
                    f"Segmento inválido detectado (distância muito pequena: {dist})"
                )

        coords, erro_fechamento = MemorialParserService._fechar_anel(coords)

        polygon = Polygon(coords)

        if polygon.is_empty:
            raise ValueError("Geometria vazia gerada do memorial")

        if not polygon.is_valid:
            polygon = polygon.buffer(0)

        if polygon.is_empty or not polygon.is_valid:
            raise ValueError("Geometria inválida gerada do memorial")

        area_m2 = float(polygon.area)
        perimetro_m = float(polygon.length)

        return {
            "geojson": polygon.__geo_interface__,
            "coords": coords,
            "segmentos": segmentos,
            "controle": {
                "total_segmentos": len(segmentos),
                "vertices": len(coords),
                "fechamento": True,
                "erro_fechamento_m": erro_fechamento,
                "area_m2": area_m2,
                "perimetro_m": perimetro_m,
                "distancia_minima_m": min(distancias_calculadas) if distancias_calculadas else None,
                "distancia_maxima_m": max(distancias_calculadas) if distancias_calculadas else None,
                "azimute_min_graus": min(azimutes_calculados) if azimutes_calculados else None,
                "azimute_max_graus": max(azimutes_calculados) if azimutes_calculados else None,
            },
        }