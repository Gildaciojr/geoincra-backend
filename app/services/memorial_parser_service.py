# app/services/memorial_parser_service.py

from __future__ import annotations

import math
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
    def _validar_componentes_dms(
        graus: float,
        minutos: float,
        segundos: float,
        limite_graus: float,
        texto_original: str,
    ) -> None:

        if graus < 0:
            raise ValueError(
                f"Graus negativos inválidos: {texto_original}"
            )

        if graus > limite_graus:
            raise ValueError(
                f"Graus fora do limite permitido: {texto_original}"
            )

        if minutos < 0 or minutos >= 60:
            raise ValueError(
                f"Minutos inválidos no azimute/rumo: {texto_original}"
            )

        if segundos < 0 or segundos >= 60:
            raise ValueError(
                f"Segundos inválidos no azimute/rumo: {texto_original}"
            )

    @staticmethod
    def _dms_para_decimal(
        graus: float,
        minutos: float,
        segundos: float,
    ) -> float:
        return (
            graus
            + (minutos / 60)
            + (segundos / 3600)
        )
    
    @staticmethod
    def _montar_dms_str(
        graus: int,
        minutos: int,
        segundos: int,
    ) -> str:
        return f"{graus}°{minutos:02d}'{segundos:02d}\""

    @staticmethod
    def _gerar_candidatos_dms_colapsado(
        valor: Any,
        *,
        limite_graus: int = 360,
    ) -> list[dict[str, Any]]:
        texto_original = str(valor or "").strip()

        texto_numerico = re.sub(
            r"[^\d]",
            "",
            texto_original,
        )

        candidatos: list[dict[str, Any]] = []

        if len(texto_numerico) < 4:
            return candidatos

        # =====================================================
        # CASO 9195040 -> 91°50'40"
        # CASO 121830 -> 121°08'30" ou 12°18'30"
        # =====================================================
        tamanhos_graus = [3, 2, 1]

        for tamanho_graus in tamanhos_graus:
            if len(texto_numerico) <= tamanho_graus:
                continue

            restante = texto_numerico[tamanho_graus:]

            if len(restante) < 2:
                continue

            graus_txt = texto_numerico[:tamanho_graus]

            try:
                graus = int(graus_txt)
            except Exception:
                continue

            if graus < 0 or graus > limite_graus:
                continue

            # -------------------------------------------------
            # DMS COMPLETO: graus + minutos(2) + segundos(2)
            # -------------------------------------------------
            if len(restante) >= 4:
                minutos_txt = restante[:2]
                segundos_txt = restante[2:4]

                try:
                    minutos = int(minutos_txt)
                    segundos = int(segundos_txt)
                except Exception:
                    minutos = -1
                    segundos = -1

                if 0 <= minutos < 60 and 0 <= segundos < 60:
                    try:
                        decimal = MemorialParserService._dms_para_decimal(
                            graus,
                            minutos,
                            segundos,
                        )

                        if 0 <= decimal <= limite_graus:
                            candidatos.append(
                                {
                                    "valor_original": texto_original,
                                    "valor_corrigido": (
                                        MemorialParserService._montar_dms_str(
                                            graus,
                                            minutos,
                                            segundos,
                                        )
                                    ),
                                    "graus": graus,
                                    "minutos": minutos,
                                    "segundos": segundos,
                                    "decimal": decimal,
                                    "tipo_recuperacao": "DMS_COLAPSADO",
                                    "confianca": 0.92,
                                }
                            )
                    except Exception:
                        pass

            # -------------------------------------------------
            # DM: graus + minutos(2)
            # Ex.: 1218 -> 12°18'
            # -------------------------------------------------
            if len(restante) == 2:
                try:
                    minutos = int(restante)
                except Exception:
                    minutos = -1

                if 0 <= minutos < 60:
                    try:
                        decimal = MemorialParserService._dms_para_decimal(
                            graus,
                            minutos,
                            0,
                        )

                        if 0 <= decimal <= limite_graus:
                            candidatos.append(
                                {
                                    "valor_original": texto_original,
                                    "valor_corrigido": (
                                        MemorialParserService._montar_dms_str(
                                            graus,
                                            minutos,
                                            0,
                                        )
                                    ),
                                    "graus": graus,
                                    "minutos": minutos,
                                    "segundos": 0,
                                    "decimal": decimal,
                                    "tipo_recuperacao": "DM_COLAPSADO",
                                    "confianca": 0.78,
                                }
                            )
                    except Exception:
                        pass

        # =====================================================
        # REMOVE DUPLICADOS POR DECIMAL
        # =====================================================
        unicos: list[dict[str, Any]] = []
        vistos: set[float] = set()

        for candidato in candidatos:
            decimal = round(float(candidato["decimal"]), 8)

            if decimal in vistos:
                continue

            vistos.add(decimal)
            unicos.append(candidato)

        unicos.sort(
            key=lambda item: (
                -float(item.get("confianca") or 0),
                abs(float(item.get("decimal") or 0)),
            )
        )

        return unicos

    @staticmethod
    def _recuperar_azimute_ocr_corrompido(
        valor: Any,
    ) -> dict[str, Any] | None:
        candidatos = (
            MemorialParserService
            ._gerar_candidatos_dms_colapsado(
                valor,
                limite_graus=360,
            )
        )

        if not candidatos:
            return None

        return candidatos[0]
                
    @staticmethod
    def _rumo_para_azimute(rumo: str) -> float:
        rumo_normalizado = (
            MemorialParserService._normalizar_texto_base(rumo)
            .upper()
        )

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

        MemorialParserService._validar_componentes_dms(
            graus=graus,
            minutos=minutos,
            segundos=segundos,
            limite_graus=90,
            texto_original=rumo,
        )

        angulo = MemorialParserService._dms_para_decimal(
            graus,
            minutos,
            segundos,
        )

        if angulo < 0 or angulo > 90:
            raise ValueError(
                f"Rumo inválido fora do quadrante: {rumo}"
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
    def _azimute_dms_para_decimal(
        azimute: str,
    ) -> float:

        azimute_normalizado = (
            MemorialParserService._normalizar_texto_base(
                azimute
            )
        )

        match = re.search(
            r"(\d{1,3})\s*[°]\s*"
            r"(\d{1,2})?\s*'?\s*"
            r"(\d{1,2}(?:\.\d+)?)?\s*\"?",
            azimute_normalizado,
        )

        if not match:
            raise ValueError(
                f"Azimute inválido: {azimute}"
            )

        g, m, s = match.groups()

        graus = float(g)
        minutos = float(m or 0)
        segundos = float(s or 0)

        MemorialParserService._validar_componentes_dms(
            graus=graus,
            minutos=minutos,
            segundos=segundos,
            limite_graus=360,
            texto_original=azimute,
        )

        decimal = (
            MemorialParserService._dms_para_decimal(
                graus,
                minutos,
                segundos,
            )
        )

        if decimal < 0 or decimal > 360:
            raise ValueError(
                "Azimute fora do intervalo válido: "
                f"{azimute}"
            )

        return decimal

    @staticmethod
    def _azimute_decimal_para_float(
        azimute: str,
    ) -> float:

        texto_original = azimute

        texto = (
            MemorialParserService._normalizar_texto_base(
                azimute
            )
        )

        texto = texto.replace(",", ".")

        # =====================================================
        # OCR-SAFE
        # =====================================================

        texto_limpo = re.sub(
            r"[^\d.\-]",
            "",
            texto,
        )

        if not texto_limpo:
            raise ValueError(
                f"Azimute decimal inválido: "
                f"{texto_original}"
            )

        # =====================================================
        # BLOQUEIO OCR COLAPSADO
        # Exemplo:
        # 9195040
        # 123304520
        # =====================================================

        if (
            "." not in texto_limpo
            and len(texto_limpo) >= 6
        ):
            recuperado = (
                MemorialParserService
                ._recuperar_azimute_ocr_corrompido(
                    texto_original
                )
            )
            if recuperado:
                return float(recuperado["decimal"])
               
            raise ValueError(
                "Azimute OCR corrompido "
                f"ou DMS colapsado: {texto_original}"
            )

        try:
            valor = float(texto_limpo)

        except Exception:
            raise ValueError(
                f"Azimute decimal inválido: "
                f"{texto_original}"
            )

        if valor < 0 or valor > 360:
            raise ValueError(
                "Azimute decimal fora do "
                f"intervalo válido: {texto_original}"
            )

        return valor

    @staticmethod
    def _parse_azimute_ou_rumo(
        valor: str,
    ) -> float:

        texto = (
            MemorialParserService._normalizar_texto_base(
                valor
            )
        )

        if not texto:
            raise ValueError(
                "Azimute/rumo vazio"
            )

        texto_upper = texto.upper()

        # =====================================================
        # OCR CORROMPIDO
        # =====================================================

        texto_numerico = re.sub(
            r"[^\d]",
            "",
            texto_upper,
        )

        if (
            len(texto_numerico) >= 6
            and "°" not in texto_upper
            and "." not in texto_upper
            and "," not in texto_upper
        ):
            recuperado = (
                MemorialParserService
                ._recuperar_azimute_ocr_corrompido(
                    valor
                )
            )

            if recuperado:
                return float(recuperado["decimal"])

            raise ValueError(
                "Azimute OCR corrompido "
                f"ou DMS colapsado: {valor}"
            )

        # =====================================================
        # RUMO QUADRANTAL
        # =====================================================

        if re.search(
            r"[NS].*[EW]",
            texto_upper,
        ):
            try:
                return (
                    MemorialParserService
                    ._rumo_para_azimute(texto)
                )

            except Exception:
                pass

        # =====================================================
        # AZIMUTE DMS
        # =====================================================

        if re.search(
            r"\d{1,3}\s*[°]\s*\d{1,2}",
            texto_upper,
        ):
            try:
                return (
                    MemorialParserService
                    ._azimute_dms_para_decimal(
                        texto
                    )
                )

            except Exception:
                pass

        # =====================================================
        # DECIMAL
        # =====================================================

        return (
            MemorialParserService
            ._azimute_decimal_para_float(
                texto
            )
        )

    @staticmethod
    def _parse_distancia(valor: Any) -> float:

        # =========================================================
        # NUMÉRICO DIRETO
        # =========================================================
        if isinstance(valor, (int, float)):

            dist = float(valor)

            if math.isnan(dist) or math.isinf(dist):
                raise ValueError(
                    "Distância inválida (NaN/Inf)"
                )

            if dist <= 0:
                raise ValueError(
                    "Distância deve ser positiva"
                )

            if dist < 0.5:
                raise ValueError(
                    f"Distância muito pequena: {dist}"
                )

            if dist > 100000:
                raise ValueError(
                    f"Distância excessiva: {dist}"
                )

            return dist

        # =========================================================
        # NORMALIZAÇÃO BASE
        # =========================================================
        texto_original = str(valor)

        texto = MemorialParserService._normalizar_texto_base(
            texto_original
        )

        if not texto:
            raise ValueError(
                "Distância vazia"
            )

        texto = texto.upper()

        # =========================================================
        # LIMPEZA OCR-SAFE
        # =========================================================
        texto = texto.replace("METROS", "")
        texto = texto.replace("METRO", "")
        texto = texto.replace("MTS", "")
        texto = texto.replace("MT", "")
        texto = texto.replace("M.", "")
        texto = texto.replace("M", "")

        texto = texto.replace(";", "")
        texto = texto.replace(":", "")

        # =========================================================
        # 🔥 OCR CONTROLADO
        # =========================================================
        #
        # 1O5,22 -> 105,22
        # 15l.33 -> 151.33
        #
        # =========================================================
        texto = re.sub(
            r"(?<=\d)[O](?=\d)",
            "0",
            texto,
        )

        texto = re.sub(
            r"(?<=\d)[LI](?=\d)",
            "1",
            texto,
        )

        texto = texto.strip()

        # =========================================================
        # REMOVE LIXO
        # =========================================================
        texto = re.sub(
            r"[^\d,.\-]",
            "",
            texto,
        )

        if not texto:
            raise ValueError(
                f"Distância inválida: {valor}"
            )

        # =========================================================
        # EXTRAÇÃO NUMÉRICA INTELIGENTE
        # =========================================================
        match = re.search(
            (
                r"(-?\d{1,3}"
                r"(?:[.,]\d{3})*"
                r"(?:[.,]\d+)?"
                r"|-?\d+(?:[.,]\d+)?)"
            ),
            texto,
        )

        if not match:
            raise ValueError(
                f"Distância inválida: {valor}"
            )

        numero_str = (
            match.group(1).strip()
        )

        # =========================================================
        # NORMALIZAÇÃO PT-BR / EN-US
        # =========================================================
        virgulas = numero_str.count(",")
        pontos = numero_str.count(".")

        # =========================================================
        # FORMATO MISTO
        # =========================================================
        if virgulas > 0 and pontos > 0:

            ultima_virgula = (
                numero_str.rfind(",")
            )

            ultimo_ponto = (
                numero_str.rfind(".")
            )

            # PT-BR
            if ultima_virgula > ultimo_ponto:

                numero_str = (
                    numero_str.replace(".", "")
                )

                numero_str = (
                    numero_str.replace(",", ".")
                )

            # EN-US
            else:

                numero_str = (
                    numero_str.replace(",", "")
                )

        # =========================================================
        # SOMENTE VÍRGULA
        # =========================================================
        elif virgulas > 0 and pontos == 0:

            partes = numero_str.split(",")

            # decimal
            if len(partes[-1]) <= 3:

                numero_str = (
                    numero_str.replace(",", ".")
                )

            # milhar
            else:

                numero_str = (
                    numero_str.replace(",", "")
                )

        # =========================================================
        # SOMENTE PONTO
        # =========================================================
        elif pontos > 0 and virgulas == 0:

            partes = numero_str.split(".")

            if len(partes) > 2:

                decimal = partes[-1]

                inteiro = "".join(
                    partes[:-1]
                )

                numero_str = (
                    f"{inteiro}.{decimal}"
                )

        # =========================================================
        # CONVERSÃO FINAL
        # =========================================================
        try:

            dist = float(numero_str)

        except Exception as exc:

            raise ValueError(
                f"Distância inválida: {valor}"
            ) from exc

        # =========================================================
        # VALIDAÇÕES
        # =========================================================
        if math.isnan(dist) or math.isinf(dist):
            raise ValueError(
                "Distância inválida (NaN/Inf)"
            )

        if dist <= 0:
            raise ValueError(
                "Distância deve ser positiva"
            )

        if dist < 0.5:
            raise ValueError(
                f"Distância muito pequena: {dist}"
            )

        if dist > 100000:
            raise ValueError(
                f"Distância excessiva: {dist}"
            )

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
            print(
                "⚠️ Distância inválida "
                f"no segmento OCR: {distancia}"
            )
            return

        if dist <= 0:
            print(
                "⚠️ Distância não positiva "
                f"ignorada: {dist}"
            )
            return

        try:
            az = float(azimute)

        except Exception:
            print(
                "⚠️ Azimute inválido "
                f"no segmento OCR: {azimute}"
            )
            return

        # =====================================================
        # PROTEÇÃO OCR / GEOMETRIA
        # =====================================================

        if az < 0 or az > 360:
            print(
                "⚠️ Segmento ignorado por "
                f"ângulo inválido: {az}"
            )
            return

        # =====================================================
        # BLOQUEIO DE OCR COLAPSADO
        # =====================================================

        rumo_texto = str(rumo_original or "").strip()

        rumo_numerico = re.sub(
            r"[^\d]",
            "",
            rumo_texto,
        )

        if (
            len(rumo_numerico) >= 6
            and "°" not in rumo_texto
            and "." not in rumo_texto
            and "," not in rumo_texto
        ):
            print(
                "⚠️ Segmento OCR corrompido "
                f"ignorado: {rumo_original}"
            )
            return

        rumo_normalizado = (
            MemorialParserService
            ._normalizar_texto_base(
                rumo_original
            )
        )

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
            vi = (
                MemorialParserService
                ._normalizar_texto_base(
                    vertice_inicial
                )
            )

            vi = re.sub(
                r"[^\w.\-_/]",
                "",
                vi,
            ).upper()

            if vi:
                segmento["vertice_inicial"] = vi

        if vertice_final:
            vf = (
                MemorialParserService
                ._normalizar_texto_base(
                    vertice_final
                )
            )

            vf = re.sub(
                r"[^\w.\-_/]",
                "",
                vf,
            ).upper()

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
            except Exception as exc:
                print(
                    "⚠️ Falha ao processar "
                    f"segmento PADRÃO 1 (rumo): "
                    f"rumo={rumo} | "
                    f"distancia={distancia} | "
                    f"erro={str(exc)}"
                )
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
            except Exception as exc:
                print(
                    "⚠️ Falha ao processar "
                    f"segmento PADRÃO 2 (azimute): "
                    f"azimute={az_str} | "
                    f"distancia={distancia} | "
                    f"erro={str(exc)}"
                )
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
            except Exception as exc:
                print(
                    "⚠️ Falha ao processar "
                    f"segmento PADRÃO 3 (cartorio): "
                    f"azimute={az_str} | "
                    f"distancia={distancia} | "
                    f"erro={str(exc)}"
                )
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
            except Exception as exc:
                print(
                    "⚠️ Falha ao processar "
                    f"segmento PADRÃO 4 "
                    f"(cartorio_na_distancia): "
                    f"azimute={az_str} | "
                    f"distancia={distancia} | "
                    f"erro={str(exc)}"
                )
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
            except Exception as exc:
                print(
                    "⚠️ Falha ao processar "
                    f"segmento PADRÃO 5 "
                    f"(cartorio_metros): "
                    f"azimute={az_str} | "
                    f"distancia={distancia} | "
                    f"erro={str(exc)}"
                )
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
            except Exception as exc:
                print(
                    "⚠️ Falha ao processar "
                    f"segmento PADRÃO 6 "
                    f"(azimute_decimal): "
                    f"azimute={az_str} | "
                    f"distancia={distancia} | "
                    f"erro={str(exc)}"
                )
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
            except Exception as exc:
                print(
                    "⚠️ Falha ao processar "
                    f"segmento PADRÃO 7 "
                    f"(vertices_rumo): "
                    f"vértice1={v1} | "
                    f"vértice2={v2} | "
                    f"rumo={rumo} | "
                    f"distancia={distancia} | "
                    f"erro={str(exc)}"
                )
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
            except Exception as exc:
                print(
                    "⚠️ Falha ao processar "
                    f"segmento PADRÃO 8 "
                    f"(vertices_azimute): "
                    f"vértice1={v1} | "
                    f"vértice2={v2} | "
                    f"azimute={azimute_raw} | "
                    f"distancia={distancia} | "
                    f"erro={str(exc)}"
                )
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
            except Exception as exc:
                print(
                    "⚠️ Falha ao processar "
                    f"segmento PADRÃO 9 "
                    f"(rumo_solto): "
                    f"rumo={rumo} | "
                    f"distancia={distancia} | "
                    f"erro={str(exc)}"
                )
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

        # =========================================================
        # 🔥 CONTROLE ESPACIAL
        # =========================================================
        minx = 0.0
        miny = 0.0
        maxx = 0.0
        maxy = 0.0

        # =========================================================
        # 🔥 CONTROLE ANGULAR
        # =========================================================
        ultimo_azimute: float | None = None

        # =========================================================
        # 🔥 LIMITES TÉCNICOS
        # =========================================================
        LIMITE_ENVELOPE_METROS = 50000.0
        LIMITE_SEGMENTO_METROS = 5000.0
        LIMITE_EXPLOSAO_FATOR = 25.0
        LIMITE_SALTO_ANGULAR = 170.0

        for idx, seg in enumerate(segmentos, start=1):

            azimute = seg.get("azimute")
            distancia = seg.get("distancia")

            if azimute is None or distancia is None:
                raise ValueError(
                    f"Segmento inválido na posição {idx}: "
                    f"azimute ou distância ausente"
                )

            try:
                az_val = float(azimute)
                dist_val = float(distancia)

            except Exception:
                raise ValueError(
                    f"Segmento inválido na posição {idx}: "
                    f"valores não numéricos"
                )

            if az_val < 0 or az_val > 360:
                raise ValueError(
                    f"Segmento inválido na posição {idx}: "
                    f"azimute fora do intervalo"
                )

            if dist_val <= 0:
                raise ValueError(
                    f"Segmento inválido na posição {idx}: "
                    f"distância não positiva"
                )

            if dist_val < MemorialParserService.DISTANCIA_MINIMA_METROS:
                raise ValueError(
                    f"Segmento inválido na posição {idx}: "
                    f"distância muito pequena ({dist_val})"
                )

            if dist_val > LIMITE_SEGMENTO_METROS:
                raise ValueError(
                    f"Segmento inválido na posição {idx}: "
                    f"distância excessiva ({dist_val})"
                )

            if distancias_calculadas:

                media_distancias = (
                    sum(distancias_calculadas)
                    / len(distancias_calculadas)
                )

                if media_distancias > 0:

                    fator_explosao = (
                        dist_val / media_distancias
                    )

                    if fator_explosao > LIMITE_EXPLOSAO_FATOR:
                        raise ValueError(
                            f"Segmento inválido na posição {idx}: "
                            f"explosão vetorial detectada "
                            f"(x{fator_explosao:.2f})"
                        )

            if ultimo_azimute is not None:

                delta_angular = abs(
                    az_val - ultimo_azimute
                )

                delta_angular = min(
                    delta_angular,
                    360 - delta_angular,
                )

                if delta_angular > LIMITE_SALTO_ANGULAR:
                    print(
                        f"Aviso: Segmento {idx} possui salto angular "
                        f"suspeito ({delta_angular:.2f}°)"
                    )

            ultimo_azimute = az_val

            az = radians(az_val)

            dx = dist_val * sin(az)
            dy = dist_val * cos(az)

            if dx != dx or dy != dy:
                raise ValueError(
                    f"Segmento inválido na posição {idx}: "
                    f"deslocamento NaN"
                )

            if abs(dx) > 1e7 or abs(dy) > 1e7:
                raise ValueError(
                    f"Segmento inválido na posição {idx}: "
                    f"deslocamento absurdo"
                )

            novo_x = x + dx
            novo_y = y + dy

            minx = min(minx, novo_x)
            miny = min(miny, novo_y)

            maxx = max(maxx, novo_x)
            maxy = max(maxy, novo_y)

            spanx = abs(maxx - minx)
            spany = abs(maxy - miny)

            if (
                spanx > LIMITE_ENVELOPE_METROS
                or spany > LIMITE_ENVELOPE_METROS
            ):
                raise ValueError(
                    f"Envelope geométrico inválido "
                    f"({spanx:.2f} x {spany:.2f})"
                )

            x = novo_x
            y = novo_y

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
        # 🔥 CORREÇÃO DE FECHAMENTO CONTROLADA
        # =========================================================
        primeiro = coords[0]
        ultimo = coords[-1]

        erro_x = ultimo[0] - primeiro[0]
        erro_y = ultimo[1] - primeiro[1]

        erro_total = sqrt(
            (erro_x ** 2)
            + (erro_y ** 2)
        )

        # =========================================================
        # 🔥 LIMITE MÁXIMO DE CORREÇÃO
        # =========================================================
        #
        # IMPORTANTE:
        #
        # Pequeno erro:
        # - aceitável
        # - comum em OCR
        #
        # Grande erro:
        # - memorial inválido
        # - rumo incorreto
        # - OCR contaminado
        # - geometria degenerada
        #
        # =========================================================
        limite_correcao = (
            MemorialParserService
            .FECHAMENTO_TOLERANCIA_METROS
            * 5
        )

        if erro_total > limite_correcao:

            raise ValueError(
                "Erro de fechamento excessivo "
                f"({erro_total:.3f} m)"
            )

        # =========================================================
        # 🔥 CORREÇÃO DISTRIBUÍDA
        # =========================================================
        if erro_total > 0:

            coords_corrigidos = [
                coords[0]
            ]

            total_vertices = (
                len(coords) - 1
            )

            if total_vertices <= 0:
                raise ValueError(
                    "Quantidade inválida "
                    "de vértices"
                )

            for i in range(
                1,
                len(coords),
            ):

                fator = (
                    i / total_vertices
                )

                novo_x = (
                    coords[i][0]
                    - (erro_x * fator)
                )

                novo_y = (
                    coords[i][1]
                    - (erro_y * fator)
                )

                coords_corrigidos.append(
                    (
                        novo_x,
                        novo_y,
                    )
                )

            coords = coords_corrigidos

        # =========================================================
        # 🔥 FECHAMENTO FINAL
        # =========================================================
        coords, erro_fechamento = (
            MemorialParserService._fechar_anel(
                coords
            )
        )

        polygon = Polygon(coords)

        # =========================================================
        # 🔥 GEOMETRIA VAZIA
        # =========================================================
        if polygon.is_empty:

            raise ValueError(
                "Geometria vazia gerada do memorial"
            )

        # =========================================================
        # 🔥 VALIDAÇÃO TOPOLOGICA
        # =========================================================
        if not polygon.is_valid:

            polygon_corrigido = polygon.buffer(0)

            # =====================================================
            # 🔥 FALHA TOTAL
            # =====================================================
            if (
                polygon_corrigido.is_empty
                or not polygon_corrigido.is_valid
            ):

                raise ValueError(
                    "Geometria inválida gerada "
                    "do memorial"
                )

            # =====================================================
            # 🔥 BLOQUEIA MULTIPOLYGON
            # =====================================================
            if (
                polygon_corrigido.geom_type
                != "Polygon"
            ):

                raise ValueError(
                    "Memorial gerou geometria "
                    "fragmentada (MultiPolygon)"
                )

            polygon = polygon_corrigido

        # =========================================================
        # 🔥 SOMENTE POLYGON
        # =========================================================
        if polygon.geom_type != "Polygon":

            raise ValueError(
                "Tipo geométrico inválido: "
                f"{polygon.geom_type}"
            )

        # =========================================================
        # 🔥 ÁREA DEGENERADA
        # =========================================================
        if polygon.area <= 0:

            raise ValueError(
                "Área geométrica inválida"
            )

        # =========================================================
        # 🔥 PERÍMETRO DEGENERADO
        # =========================================================
        if polygon.length <= 0:

            raise ValueError(
                "Perímetro geométrico inválido"
            )

        area_m2 = float(
            polygon.area
        )

        perimetro_m = float(
            polygon.length
        )

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
