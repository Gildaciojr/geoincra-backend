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
        texto = str(texto or "")

        return (
            MemorialParserService._normalizar_espacos(texto)
            .replace("–", "-")
            .replace("—", "-")
            .replace("−", "-")
            .replace("“", '"')
            .replace("”", '"')
            .replace("´", "'")
            .replace("`", "'")
            .replace("’", "'")
            .replace("″", '"')
            .replace("′", "'")
            .replace("º", "°")
            .replace("˚", "°")
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
            r"([NS])\s*"
            r"(\d{1,3})\s*[°]\s*"
            r"(\d{1,2})?\s*'?\s*"
            r"(\d{1,2}(?:\.\d+)?)?\s*\"?\s*"
            r"([EW])",
            rumo_normalizado,
        )

        if not match:
            raise ValueError(f"Rumo inválido: {rumo}")

        ns, g, m, s, ew = match.groups()

        graus = float(g)
        minutos = float(m or 0)
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
            r"(\d{1,3})\s*[°]\s*"
            r"(\d{1,2})?\s*'?\s*"
            r"(\d{1,2}(?:\.\d+)?)?\s*\"?",
            azimute_normalizado,
        )

        if not match:
            raise ValueError(f"Azimute inválido: {azimute}")

        g, m, s = match.groups()

        decimal = MemorialParserService._dms_para_decimal(
            float(g),
            float(m or 0),
            float(s or 0),
        )

        if decimal < 0 or decimal > 360:
            raise ValueError(f"Azimute fora do intervalo válido: {azimute}")

        return decimal

    @staticmethod
    def _azimute_decimal_para_float(azimute: str) -> float:
        texto = MemorialParserService._normalizar_texto_base(azimute)

        # limpeza agressiva OCR-safe (sem quebrar casos válidos)
        texto = texto.replace(",", ".")
        texto = re.sub(r"[^\d.\-]", "", texto)

        if not texto:
            raise ValueError(f"Azimute decimal inválido: {azimute}")

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

        if not texto:
            raise ValueError("Azimute/rumo vazio")

        texto_upper = texto.upper()

        # =========================================================
        # 1. PRIMEIRO TENTA RUMO QUADRANTAL
        # Exemplos aceitos:
        # N 45°30'20" E
        # N45°30'20"E
        # S 12° E
        # =========================================================
        if re.search(r"[NS].*[EW]", texto_upper):
            try:
                return MemorialParserService._rumo_para_azimute(texto)
            except Exception:
                pass

        # =========================================================
        # 2. DEPOIS TENTA AZIMUTE EM DMS
        # Exemplos:
        # 123°45'20"
        # 123°45'
        # 123° 45 20
        # =========================================================
        if re.search(r"\d{1,3}\s*[°]\s*\d{1,2}", texto_upper):
            try:
                return MemorialParserService._azimute_dms_para_decimal(texto)
            except Exception:
                pass

        # =========================================================
        # 3. POR ÚLTIMO TENTA DECIMAL PURO
        # Exemplos:
        # 123.456789
        # 123,456789
        # =========================================================
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

        # =========================================================
        # LIMPEZA OCR-SAFE
        # =========================================================
        texto = texto.replace("metros", "")
        texto = texto.replace("metro", "")
        texto = texto.replace("mts", "")
        texto = texto.replace("mt", "")
        texto = texto.replace("m.", "")
        texto = texto.replace("m", "")
        texto = texto.replace(";", "")
        texto = texto.replace(":", "")
        texto = texto.strip()

        # remove lixo preservando dígitos, vírgula, ponto e sinal
        texto = re.sub(r"[^\d,.\-]", "", texto)

        if not texto:
            raise ValueError(f"Distância inválida: {valor}")

        # =========================================================
        # NORMALIZAÇÃO NUMÉRICA
        # Casos:
        # 1.234,56 -> 1234.56
        # 1234,56 -> 1234.56
        # 1,234.56 -> 1234.56
        # 1234.56 -> 1234.56
        # =========================================================
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
        dx = float(p2[0]) - float(p1[0])
        dy = float(p2[1]) - float(p1[1])

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

        if erro_fechamento < 0:
            raise ValueError("Erro de fechamento inválido")

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
        try:
            dist = float(distancia)
        except Exception:
            return

        if dist <= 0:
            return

        try:
            az = float(azimute)
        except Exception:
            return

        # proteção adicional contra valores inválidos
        if az < 0 or az > 360:
            return

        rumo_normalizado = MemorialParserService._normalizar_texto_base(rumo_original)

        segmento: dict[str, Any] = {
            "tipo": tipo,
            "rumo": rumo_normalizado,
            "azimute": az,
            "distancia": dist,
        }

        if ordem is not None:
            try:
                segmento["ordem"] = int(ordem)
            except Exception:
                segmento["ordem"] = ordem

        if vertice_inicial:
            vi = MemorialParserService._normalizar_texto_base(vertice_inicial)
            vi = re.sub(r"[^\w.\-_/]", "", vi).upper()
            if vi:
                segmento["vertice_inicial"] = vi

        if vertice_final:
            vf = MemorialParserService._normalizar_texto_base(vertice_final)
            vf = re.sub(r"[^\w.\-_/]", "", vf).upper()
            if vf:
                segmento["vertice_final"] = vf

        segmentos.append(segmento)

    @staticmethod
    def _deduplicar_segmentos(segmentos: list[dict[str, Any]]) -> list[dict[str, Any]]:
        segmentos_unicos: list[dict[str, Any]] = []
        vistos: set[tuple[str, float, float]] = set()

        for seg in segmentos:
            try:
                rumo = str(seg.get("rumo", "")).strip().upper()

                az = float(seg.get("azimute", 0.0))
                dist = float(seg.get("distancia", 0.0))

                # arredondamento controlado (OCR gera pequenas variações)
                az_round = round(az, 6)
                dist_round = round(dist, 4)

                chave = (rumo, az_round, dist_round)

            except Exception:
                continue

            if chave in vistos:
                continue

            vistos.add(chave)
            segmentos_unicos.append(seg)

        # ordenação segura (mantendo comportamento atual)
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
            r"azimute\s*(?:de)?\s*(\d+[°]\s*\d+'?\s*\d*(?:\.\d+)?\"?)"
            r".{0,60}?"
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
            r"azimute\s*de\s*(\d+[°]\s*\d+'?\s*\d*(?:\.\d+)?\"?)"
            r".{0,120}?"
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
            r"azimute\s*de\s*(\d+[°]\s*\d+'?\s*\d*(?:\.\d+)?\"?)"
            r".{0,140}?"
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
        # PADRÃO 5: VARIAÇÃO COM "metros"
        # =========================================================
        pattern_cartorio_metros = re.compile(
            r"azimute\s*de\s*(\d+[°]\s*\d+'?\s*\d*(?:\.\d+)?\"?)"
            r".{0,160}?"
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
        # PADRÃO 6: AZIMUTE DECIMAL
        # =========================================================
        pattern_azimute_decimal = re.compile(
            r"azimute\s*(?:de)?\s*(\d+(?:[.,]\d+)?)"
            r".{0,80}?"
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
        # PADRÃO 7: VÉRTICES + RUMO
        # =========================================================
        pattern_vertices_rumo = re.compile(
            r"(?:v[eé]rtice|marco)\s*([A-Z0-9.\-_/]+)"
            r".{0,80}?"
            r"(?:ao|até|ate)\s*(?:v[eé]rtice|marco)?\s*([A-Z0-9.\-_/]+)"
            r".{0,120}?"
            r"rumo\s*(.*?)\s*"
            r".{0,80}?"
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
        # PADRÃO 8: VÉRTICES + AZIMUTE
        # =========================================================
        pattern_vertices_azimute = re.compile(
            r"(?:v[eé]rtice|marco)\s*([A-Z0-9.\-_/]+)"
            r".{0,80}?"
            r"(?:ao|até|ate)\s*(?:v[eé]rtice|marco)?\s*([A-Z0-9.\-_/]+)"
            r".{0,140}?"
            r"azimute\s*(?:de)?\s*(\d+[°]\s*\d+'?\s*\d*(?:\.\d+)?\"?|\d+(?:[.,]\d+)?)"
            r".{0,80}?"
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

        # =========================================================
        # PADRÃO 9 (NOVO): RUMO + DISTÂNCIA SEM PALAVRAS-CHAVE
        # =========================================================
        pattern_rumo_solto = re.compile(
            r"(N\s*\d+[°]\s*\d+'?\s*\d*(?:\.\d+)?\"?\s*[EW])"
            r".{0,120}?"
            r"(\d+(?:[.,]\d+)?)\s*(?:m|metros)?",
            re.IGNORECASE | re.DOTALL,
        )

        for rumo, distancia in pattern_rumo_solto.findall(texto):
            try:
                az = MemorialParserService._rumo_para_azimute(rumo)
                dist = MemorialParserService._parse_distancia(distancia)

                MemorialParserService._adicionar_segmento(
                    segmentos=segmentos,
                    tipo="rumo_solto",
                    rumo_original=rumo,
                    azimute=az,
                    distancia=dist,
                )
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

        # =========================================================
        # ORDENAÇÃO SEGURA (sem quebrar comportamento)
        # =========================================================
        try:
            segmentos = sorted(
                segmentos,
                key=lambda s: (
                    0 if s.get("ordem") is not None else 1,
                    s.get("ordem") if s.get("ordem") is not None else 999999,
                )
            )
        except Exception:
            pass

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

            try:
                az_val = float(azimute)
                dist_val = float(distancia)
            except Exception:
                raise ValueError(f"Segmento inválido na posição {idx}: valores não numéricos")

            if az_val < 0 or az_val > 360:
                raise ValueError(f"Segmento inválido na posição {idx}: azimute fora do intervalo")

            if dist_val <= 0:
                raise ValueError(f"Segmento inválido na posição {idx}: distância não positiva")

            if dist_val < MemorialParserService.DISTANCIA_MINIMA_METROS:
                raise ValueError(
                    f"Segmento inválido na posição {idx}: distância muito pequena ({dist_val})"
                )

            az = radians(az_val)

            dx = dist_val * sin(az)
            dy = dist_val * cos(az)

            x += dx
            y += dy

            coords.append((x, y))

            distancias_calculadas.append(dist_val)
            azimutes_calculados.append(az_val)

        if len(coords) < 4:
            raise ValueError("Geometria inválida: número insuficiente de vértices")

        # =========================================================
        # VALIDAÇÃO DE SEGMENTOS (mantida + mais segura)
        # =========================================================
        for i in range(len(coords) - 1):
            dx = coords[i + 1][0] - coords[i][0]
            dy = coords[i + 1][1] - coords[i][1]

            dist = sqrt(dx * dx + dy * dy)

            if dist < MemorialParserService.DISTANCIA_MINIMA_METROS:
                raise ValueError(
                    f"Segmento inválido detectado (distância muito pequena: {dist})"
                )

        # =========================================================
        # CORREÇÃO DE FECHAMENTO (NÍVEL PROFISSIONAL)
        # =========================================================
        primeiro = coords[0]
        ultimo = coords[-1]

        erro_x = ultimo[0] - primeiro[0]
        erro_y = ultimo[1] - primeiro[1]

        erro_total = sqrt((erro_x ** 2) + (erro_y ** 2))

        if erro_total > 0:
            coords_corrigidos = [coords[0]]

            total_vertices = len(coords) - 1

            for i in range(1, len(coords)):
                fator = i / total_vertices

                novo_x = coords[i][0] - (erro_x * fator)
                novo_y = coords[i][1] - (erro_y * fator)

                coords_corrigidos.append((novo_x, novo_y))

            coords = coords_corrigidos

        # =========================================================
        # FECHAMENTO FINAL (mantido)
        # =========================================================
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