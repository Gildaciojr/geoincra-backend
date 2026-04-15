from __future__ import annotations

import math
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from shapely.geometry import Polygon

from app.services.geometria_service import GeometriaService


class CadExportService:

    # =========================================================
    # CONFIGURAÇÕES TÉCNICAS
    # =========================================================

    VERTEX_TEXT_HEIGHT = 1.6
    CONFRONTANTE_TEXT_HEIGHT = 1.8
    CONFRONTANTE_OFFSET_BASE = 2.5
    CONFRONTANTE_OFFSET_STEP = 1.5
    SEGMENT_LABEL_TEXT_HEIGHT = 1.5

    # =========================================================
    # HELPERS
    # =========================================================

    @staticmethod
    def _safe_float(value) -> float:
        try:
            v = float(value)

            if math.isnan(v) or math.isinf(v):
                return 0.0

            return v

        except Exception:
            return 0.0

    @staticmethod
    def _sanear_coords(
        coords: List[Tuple[float, float]],
    ) -> List[Tuple[float, float]]:

        coords_validos: List[Tuple[float, float]] = []

        for x, y in coords:

            xf = CadExportService._safe_float(x)
            yf = CadExportService._safe_float(y)

            if (
                math.isnan(xf)
                or math.isnan(yf)
                or math.isinf(xf)
                or math.isinf(yf)
            ):
                continue

            coords_validos.append((xf, yf))

        return coords_validos

    @staticmethod
    def _segment_midpoint(
        p1: Tuple[float, float],
        p2: Tuple[float, float],
    ) -> Tuple[float, float]:

        return (
            (float(p1[0]) + float(p2[0])) / 2.0,
            (float(p1[1]) + float(p2[1])) / 2.0,
        )

    @staticmethod
    def _distancia(
        p1: Tuple[float, float],
        p2: Tuple[float, float],
    ) -> float:

        dx = float(p2[0]) - float(p1[0])
        dy = float(p2[1]) - float(p1[1])

        return math.sqrt((dx * dx) + (dy * dy))

    @staticmethod
    def _escape_scr_text(texto: str) -> str:

        texto_limpo = str(texto or "").strip()

        # remove múltiplos espaços
        texto_limpo = " ".join(texto_limpo.split())

        return texto_limpo

    @staticmethod
    def _calcular_angulo_segmento(
        p1: Tuple[float, float],
        p2: Tuple[float, float],
    ) -> float:

        dx = float(p2[0]) - float(p1[0])
        dy = float(p2[1]) - float(p1[1])

        # segmento degenerado
        if dx == 0.0 and dy == 0.0:
            return 0.0

        angulo = math.degrees(math.atan2(dy, dx))

        # =========================================================
        # 🔥 NORMALIZAÇÃO PARA LEITURA EM CAD
        # evita texto invertido
        # =========================================================
        if angulo > 90.0:
            angulo -= 180.0
        elif angulo < -90.0:
            angulo += 180.0

        return angulo

    @staticmethod
    def _vetor_normal_unitario(
        p1: Tuple[float, float],
        p2: Tuple[float, float],
    ) -> Tuple[float, float]:

        dx = float(p2[0]) - float(p1[0])
        dy = float(p2[1]) - float(p1[1])

        comprimento = math.sqrt((dx * dx) + (dy * dy))

        if comprimento <= 0.0:
            return (0.0, 0.0)

        # =========================================================
        # 🔥 NORMAL PERPENDICULAR UNITÁRIA
        # usada para deslocamento técnico de textos
        # =========================================================
        nx = -dy / comprimento
        ny = dx / comprimento

        return (nx, ny)
    
    # =========================================================
    # SEGMENTOS (🔥 BLOCO TÉCNICO PROFISSIONAL)
    # =========================================================

    @staticmethod
    def _deg_to_dms_str(deg: float) -> str:

        deg = CadExportService._safe_float(deg)

        if math.isnan(deg) or math.isinf(deg):
            return "00°00'00.00\""

        deg = deg % 360.0

        d = int(deg)
        minutos_total = (deg - d) * 60.0
        m = int(minutos_total)
        s = (minutos_total - m) * 60.0

        s = round(s, 2)

        if s >= 60.0:
            s = 0.0
            m += 1

        if m >= 60:
            m = 0
            d += 1

        if d >= 360:
            d = 0

        return f"{d:02d}°{m:02d}'{s:05.2f}\""

    @staticmethod
    def _rumo_from_azimute(az: float) -> str:

        az = CadExportService._safe_float(az)

        if math.isnan(az) or math.isinf(az):
            return "N 00°00'00.00\" E"

        az = az % 360.0

        if 0 <= az < 90:
            ang = az
            prefixo = "N"
            sufixo = "E"

        elif 90 <= az < 180:
            ang = 180.0 - az
            prefixo = "S"
            sufixo = "E"

        elif 180 <= az < 270:
            ang = az - 180.0
            prefixo = "S"
            sufixo = "W"

        else:
            ang = 360.0 - az
            prefixo = "N"
            sufixo = "W"

        return f"{prefixo} {CadExportService._deg_to_dms_str(ang)} {sufixo}"

    @staticmethod
    def _gerar_comandos_segmentos(
        coords: List[Tuple[float, float]],
    ) -> List[str]:

        comandos: List[str] = []

        total_segmentos = len(coords) - 1

        for i in range(total_segmentos):

            p1 = coords[i]
            p2 = coords[i + 1]

            distancia = CadExportService._distancia(p1, p2)

            if distancia <= 0:
                continue

            dx = float(p2[0]) - float(p1[0])
            dy = float(p2[1]) - float(p1[1])

            azimute = math.degrees(math.atan2(dx, dy))
            if azimute < 0:
                azimute += 360.0

            rumo = CadExportService._rumo_from_azimute(azimute)

            mx, my = CadExportService._segment_midpoint(p1, p2)
            nx, ny = CadExportService._vetor_normal_unitario(p1, p2)

            # 🔥 OFFSET MAIS SUAVE (MENOS POLUIÇÃO)
            offset = 0.9

            px = mx + (nx * offset)
            py = my + (ny * offset)

            angulo = CadExportService._calcular_angulo_segmento(p1, p2)

            # =========================================================
            # 🔥 TEXTO PROFISSIONAL (REDUZIDO E LIMPO)
            # =========================================================
            texto = f"{distancia:.2f} m"

            comandos.append("._TEXT")
            comandos.append(f"{px:.6f},{py:.6f}")
            comandos.append(f"{CadExportService.SEGMENT_LABEL_TEXT_HEIGHT:.2f}")
            comandos.append(f"{angulo:.6f}")
            comandos.append(texto)

        return comandos

    # =========================================================
    # CONFRONTANTES
    # =========================================================

    @staticmethod
    def _montar_texto_confrontante(
        confrontante: Dict[str, Optional[str]],
    ) -> Optional[str]:

        nome = str(confrontante.get("nome") or "").strip()
        descricao = str(confrontante.get("descricao") or "").strip()
        lote = str(confrontante.get("lote") or "").strip()
        gleba = str(confrontante.get("gleba") or "").strip()
        matricula = str(
            confrontante.get("matricula")
            or confrontante.get("matricula_confrontante")
            or ""
        ).strip()

        texto_principal = nome or descricao
        if not texto_principal:
            return None

        complemento: List[str] = []

        if lote:
            complemento.append(f"Lote {lote}")

        if gleba:
            complemento.append(f"Gleba {gleba}")

        if matricula:
            complemento.append(f"Mat {matricula}")

        texto_final = texto_principal

        if complemento:
            texto_final += " | " + " | ".join(complemento)

        return CadExportService._escape_scr_text(texto_final)

    @staticmethod
    def _gerar_comandos_confrontantes(
        coords: List[Tuple[float, float]],
        confrontantes: List[Dict[str, Optional[str]]],
    ) -> List[str]:

        if not confrontantes:
            return []

        comandos: List[str] = []
        usados_por_segmento: Dict[int, int] = {}

        total_segmentos = len(coords) - 1

        for idx, c in enumerate(confrontantes, start=1):

            texto = CadExportService._montar_texto_confrontante(c)
            if not texto:
                continue

            ordem = c.get("ordem_segmento")

            if ordem and isinstance(ordem, int):
                seg_index = ordem - 1
            else:
                # fallback seguro para não quebrar exportação
                seg_index = min(idx - 1, total_segmentos - 1)

            seg_index = max(0, min(seg_index, total_segmentos - 1))

            p1 = coords[seg_index]
            p2 = coords[seg_index + 1]

            mx, my = CadExportService._segment_midpoint(p1, p2)
            nx, ny = CadExportService._vetor_normal_unitario(p1, p2)

            count = usados_por_segmento.get(seg_index, 0)
            usados_por_segmento[seg_index] = count + 1

            deslocamento = (
                CadExportService.CONFRONTANTE_OFFSET_BASE
                + count * CadExportService.CONFRONTANTE_OFFSET_STEP
            )

            px = mx + (nx * deslocamento)
            py = my + (ny * deslocamento)

            angulo = CadExportService._calcular_angulo_segmento(p1, p2)

            comandos.append("._TEXT")
            comandos.append(f"{px:.6f},{py:.6f}")
            comandos.append(f"{CadExportService.CONFRONTANTE_TEXT_HEIGHT:.2f}")
            comandos.append(f"{angulo:.6f}")
            comandos.append(texto)

        return comandos
    
    # =========================================================
    # GERAR SCRIPT AUTOCAD
    # =========================================================

    @staticmethod
    def gerar_scr(
        geojson: str,
        confrontantes: Optional[List[Dict[str, Optional[str]]]] = None,
    ) -> str:

        try:
            geom: Polygon = GeometriaService._parse_polygon_geojson(geojson)

        except Exception as exc:
            raise ValueError("GeoJSON inválido para exportação CAD") from exc

        # =========================================================
        # 🔥 EXTRAÇÃO E SANITIZAÇÃO
        # =========================================================
        coords = list(geom.exterior.coords)
        coords = CadExportService._sanear_coords(coords)

        if len(coords) < 4:
            raise ValueError("Polígono inválido para CAD")

        # garantir fechamento
        if coords[0] != coords[-1]:
            coords.append(coords[0])

        lines: List[str] = []

        # =========================================================
        # 🔥 INÍCIO DO BLOCO DE DESENHO
        # =========================================================
        lines.append("._UNDO _BEGIN")
        lines.append("._INSUNITS 6")  # metros

        # =========================================================
        # 🔥 DEFINIÇÃO DE CAMADAS
        # =========================================================
        lines.append("._LAYER M PERIMETRO C 2 PERIMETRO")
        lines.append("._LAYER M VERTICES C 7 VERTICES")
        lines.append("._LAYER M TEXTO_VERTICES C 3 TEXTO_VERTICES")
        lines.append("._LAYER M SEGMENTOS C 4 SEGMENTOS")
        lines.append("._LAYER M CONFRONTANTES C 1 CONFRONTANTES")

        # =========================================================
        # 🔥 POLILINHA DO PERÍMETRO
        # =========================================================
        lines.append("._LAYER S PERIMETRO")
        lines.append("._PLINE")

        for x, y in coords:
            lines.append(f"{x:.6f},{y:.6f}")

        lines.append("C")

        # =========================================================
        # 🔥 VÉRTICES
        # =========================================================
        lines.append("._LAYER S VERTICES")

        for x, y in coords[:-1]:
            lines.append("._POINT")
            lines.append(f"{x:.6f},{y:.6f}")

        # =========================================================
        # 🔥 TEXTO DOS VÉRTICES
        # =========================================================
        lines.append("._LAYER S TEXTO_VERTICES")

        for i, (x, y) in enumerate(coords[:-1], start=1):

            lines.append("._TEXT")
            lines.append(f"{x:.6f},{y:.6f}")
            lines.append(f"{CadExportService.VERTEX_TEXT_HEIGHT:.2f}")
            lines.append("0")
            lines.append(f"V{i}")

        # =========================================================
        # 🔥 SEGMENTOS (DISTÂNCIA + AZIMUTE + RUMO)
        # =========================================================
        lines.append("._LAYER S SEGMENTOS")

        comandos_segmentos = CadExportService._gerar_comandos_segmentos(coords)

        if comandos_segmentos:
            lines.extend(comandos_segmentos)

        # =========================================================
        # 🔥 CONFRONTANTES (ALINHADOS COM BANCO)
        # =========================================================
        if confrontantes:

            lines.append("._LAYER S CONFRONTANTES")

            comandos_confrontantes = (
                CadExportService._gerar_comandos_confrontantes(
                    coords,
                    confrontantes,
                )
            )

            if comandos_confrontantes:
                lines.extend(comandos_confrontantes)

        # =========================================================
        # 🔥 FINALIZAÇÃO
        # =========================================================
        lines.append("._UNDO _END")

        return "\n".join(lines)

    # =========================================================
    # SALVAR SCRIPT
    # =========================================================

    @staticmethod
    def salvar_scr(
        imovel_id: int,
        scr: str,
        base_dir: str = "app/uploads/imoveis",
    ) -> str:

        if not imovel_id:
            raise ValueError("imovel_id inválido para salvar SCR")

        if not scr or not isinstance(scr, str):
            raise ValueError("Conteúdo SCR inválido")

        # =========================================================
        # 🔥 TIMESTAMP
        # =========================================================
        ts = int(datetime.utcnow().timestamp())

        # =========================================================
        # 🔥 NORMALIZAÇÃO DE PATH
        # =========================================================
        base_dir = base_dir.strip().rstrip("/\\")
        folder = os.path.join(base_dir, str(imovel_id), "cad")

        try:
            os.makedirs(folder, exist_ok=True)
        except Exception as exc:
            raise RuntimeError("Erro ao criar diretório CAD") from exc

        # =========================================================
        # 🔥 NOME DO ARQUIVO
        # =========================================================
        filename = f"perimetro_{ts}.scr"
        path = os.path.join(folder, filename)

        # =========================================================
        # 🔥 ESCRITA SEGURA
        # =========================================================
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(scr)
        except Exception as exc:
            raise RuntimeError("Erro ao salvar arquivo SCR") from exc

        # =========================================================
        # 🔥 VALIDAÇÃO FINAL
        # =========================================================
        if not os.path.exists(path):
            raise RuntimeError("Arquivo SCR não foi criado corretamente")

        return path