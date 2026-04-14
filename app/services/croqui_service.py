# app/services/croqui_service.py

from __future__ import annotations

import json
import math
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException
from shapely.geometry import Polygon
from app.services.geometria_service import GeometriaService


class CroquiService:

    SVG_SIZE = 1100
    DRAW_PAD = 130
    HEADER_H = 90
    FOOTER_H = 140
    RIGHT_INFO_W = 250
    GRID_STEP = 80

    @staticmethod
    def _safe_float(value: float) -> float:
        try:
            v = float(value)
            if math.isnan(v) or math.isinf(v):
                return 0.0
            return v
        except Exception:
            return 0.0

    @staticmethod
    def _distancia(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        dx = float(p2[0]) - float(p1[0])
        dy = float(p2[1]) - float(p1[1])
        return math.sqrt((dx * dx) + (dy * dy))

    @staticmethod
    def _polygon_area(coords: List[Tuple[float, float]]) -> float:
        if len(coords) < 4:
            return 0.0

        area = 0.0
        for i in range(len(coords) - 1):
            x1, y1 = coords[i]
            x2, y2 = coords[i + 1]
            area += (x1 * y2) - (x2 * y1)

        return abs(area) / 2.0

    @staticmethod
    def _polygon_perimeter(coords: List[Tuple[float, float]]) -> float:
        if len(coords) < 2:
            return 0.0

        total = 0.0
        for i in range(len(coords) - 1):
            total += CroquiService._distancia(coords[i], coords[i + 1])

        return total

    @staticmethod
    def _format_num(value: float, decimals: int = 2) -> str:
        try:
            return f"{float(value):,.{decimals}f}".replace(",", "X").replace(".", ",").replace("X", ".")
        except Exception:
            return "0,00"

    @staticmethod
    def _escape_xml(text: str) -> str:
        return (
            str(text or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&apos;")
        )

    @staticmethod
    def _normalizar_geojson(geojson: Any) -> Dict[str, Any]:
        if geojson is None:
            raise HTTPException(status_code=400, detail="GeoJSON ausente.")

        obj = geojson

        if isinstance(obj, str):
            texto = obj.strip()
            if not texto:
                raise HTTPException(status_code=400, detail="GeoJSON vazio.")
            try:
                obj = json.loads(texto)
            except Exception as exc:
                raise HTTPException(status_code=400, detail="GeoJSON inválido.") from exc

        if not isinstance(obj, dict):
            raise HTTPException(status_code=400, detail="GeoJSON em formato inválido.")

        tipo = obj.get("type")

        if tipo == "FeatureCollection":
            features = obj.get("features") or []
            if not isinstance(features, list) or not features:
                raise HTTPException(
                    status_code=400,
                    detail="FeatureCollection sem features válidas.",
                )

            primeira_feature = features[0]
            if not isinstance(primeira_feature, dict):
                raise HTTPException(
                    status_code=400,
                    detail="Feature inválida na FeatureCollection.",
                )

            geometry = primeira_feature.get("geometry")
            if not isinstance(geometry, dict):
                raise HTTPException(
                    status_code=400,
                    detail="FeatureCollection sem geometria válida.",
                )

            return geometry

        if tipo == "Feature":
            geometry = obj.get("geometry")
            if not isinstance(geometry, dict):
                raise HTTPException(
                    status_code=400,
                    detail="Feature sem geometria válida.",
                )
            return geometry

        return obj

    @staticmethod
    def _parse_polygon(geojson: Any) -> Polygon:
        geojson_normalizado = CroquiService._normalizar_geojson(geojson)
        return GeometriaService.parse_polygon_or_raise(geojson_normalizado)

    @staticmethod
    def _drawing_bounds(size: int) -> Dict[str, float]:
        left = CroquiService.DRAW_PAD
        top = CroquiService.HEADER_H + 30
        right = size - CroquiService.RIGHT_INFO_W - 30
        bottom = size - CroquiService.FOOTER_H

        return {
            "left": left,
            "top": top,
            "right": right,
            "bottom": bottom,
            "width": right - left,
            "height": bottom - top,
        }

    @staticmethod
    def _normalize_points(
        coords: List[Tuple[float, float]],
        size: int,
    ) -> Tuple[List[Tuple[float, float]], float, Dict[str, float]]:
        if not coords:
            raise HTTPException(status_code=400, detail="Sem coordenadas para gerar croqui.")

        xs = [float(c[0]) for c in coords]
        ys = [float(c[1]) for c in coords]

        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)

        w = (maxx - minx) if (maxx - minx) != 0 else 1.0
        h = (maxy - miny) if (maxy - miny) != 0 else 1.0

        draw = CroquiService._drawing_bounds(size)

        scale = min(draw["width"] / w, draw["height"] / h)

        used_w = w * scale
        used_h = h * scale

        offset_x = draw["left"] + (draw["width"] - used_w) / 2.0
        offset_y = draw["top"] + (draw["height"] - used_h) / 2.0

        norm = []
        for x, y in coords:
            nx = ((float(x) - minx) * scale) + offset_x
            ny = ((maxy - float(y)) * scale) + offset_y
            norm.append((nx, ny))

        return norm, scale, {
            "minx": minx,
            "maxx": maxx,
            "miny": miny,
            "maxy": maxy,
            "width_original": w,
            "height_original": h,
            "offset_x": offset_x,
            "offset_y": offset_y,
        }

    @staticmethod
    def _segment_midpoint(p1: Tuple[float, float], p2: Tuple[float, float]) -> Tuple[float, float]:
        return (
            (float(p1[0]) + float(p2[0])) / 2.0,
            (float(p1[1]) + float(p2[1])) / 2.0
        )

    @staticmethod
    def _render_grid(size: int) -> str:
        draw = CroquiService._drawing_bounds(size)
        lines = []

        left = float(draw["left"])
        right = float(draw["right"])
        top = float(draw["top"])
        bottom = float(draw["bottom"])

        step = float(CroquiService.GRID_STEP or 1)

        # Linhas verticais
        x = left
        while x <= right:
            lines.append(
                f'<line x1="{x:.2f}" y1="{top:.2f}" x2="{x:.2f}" y2="{bottom:.2f}" '
                f'stroke="#E5E7EB" stroke-width="1"/>'
            )
            x += step

        # Linhas horizontais
        y = top
        while y <= bottom:
            lines.append(
                f'<line x1="{left:.2f}" y1="{y:.2f}" x2="{right:.2f}" y2="{y:.2f}" '
                f'stroke="#E5E7EB" stroke-width="1"/>'
            )
            y += step

        return "\n".join(lines)

    @staticmethod
    def _render_header(size: int) -> str:
        size = float(size)

        return f"""
        <g>
            <rect x="0" y="0" width="{size:.2f}" height="{CroquiService.HEADER_H}" fill="#0F172A"/>
            <text x="{size / 2:.2f}" y="34" text-anchor="middle"
                  font-size="26" font-family="Arial" font-weight="bold" fill="#FFFFFF">
                  CROQUI DO IMÓVEL
            </text>
            <text x="{size / 2:.2f}" y="62" text-anchor="middle"
                  font-size="12" font-family="Arial" fill="#CBD5E1">
                  Representação gráfica do perímetro gerada automaticamente pelo GeoINCRA
            </text>
        </g>
        """

    @staticmethod
    def _render_footer(size: int) -> str:
        size = float(size)
        footer_y = size - CroquiService.FOOTER_H + 20

        return f"""
        <g>
            <rect x="0" y="{size - CroquiService.FOOTER_H:.2f}" width="{size:.2f}" height="{CroquiService.FOOTER_H}" fill="#F8FAFC" stroke="#CBD5E1"/>
            <text x="40" y="{footer_y:.2f}" font-size="12" font-family="Arial" font-weight="bold" fill="#0F172A">
                Documento técnico gerado automaticamente
            </text>
            <text x="40" y="{footer_y + 22:.2f}" font-size="11" font-family="Arial" fill="#334155">
                Este croqui possui finalidade técnica ilustrativa e deve ser interpretado em conjunto com memorial,
                geometria e demais documentos do processo.
            </text>
            <text x="40" y="{footer_y + 44:.2f}" font-size="11" font-family="Arial" fill="#334155">
                GeoINCRA • Pipeline OCR + IA + Geometria + Documentação Técnica
            </text>
        </g>
        """

    @staticmethod
    def _render_north_arrow(size: int) -> str:
        size = float(size)

        x = size - CroquiService.RIGHT_INFO_W + 80
        y = CroquiService.HEADER_H + 40

        return f"""
        <g transform="translate({x:.2f},{y:.2f})">
          <line x1="0" y1="45" x2="0" y2="0" stroke="#0F172A" stroke-width="4"/>
          <polygon points="0,-14 -11,8 11,8" fill="#0F172A"/>
          <text x="0" y="68" text-anchor="middle" font-size="18" font-family="Arial" font-weight="bold" fill="#0F172A">N</text>
        </g>
        """

    @staticmethod
    def _render_scale_bar(size: int, scale: float) -> str:
        # barra em metros proporcional ao espaço normalizado
        candidatos = [25, 50, 100, 200, 500, 1000]

        pixels_por_metro = float(scale) if scale and scale > 0 else 1.0

        escolhido = 100
        for c in candidatos:
            px = c * pixels_por_metro
            if 90 <= px <= 220:
                escolhido = c
                break

        largura_px = escolhido * pixels_por_metro

        x0 = 50.0
        y0 = float(size) - 70.0

        return f"""
        <g transform="translate({x0:.2f},{y0:.2f})">
            <line x1="0" y1="0" x2="{largura_px:.2f}" y2="0" stroke="#111827" stroke-width="3"/>
            <line x1="0" y1="-7" x2="0" y2="7" stroke="#111827" stroke-width="2"/>
            <line x1="{largura_px/2:.2f}" y1="-7" x2="{largura_px/2:.2f}" y2="7" stroke="#111827" stroke-width="2"/>
            <line x1="{largura_px:.2f}" y1="-7" x2="{largura_px:.2f}" y2="7" stroke="#111827" stroke-width="2"/>

            <text x="0" y="22" font-size="11" font-family="Arial" fill="#111827">0</text>
            <text x="{(largura_px/2)-10:.2f}" y="22" font-size="11" font-family="Arial" fill="#111827">{int(escolhido/2)}</text>
            <text x="{largura_px-5:.2f}" y="22" font-size="11" font-family="Arial" fill="#111827">{escolhido} m</text>
        </g>
        """

    @staticmethod
    def _render_legenda(size: int) -> str:
        size = float(size)

        x = size - CroquiService.RIGHT_INFO_W + 20
        y = size - CroquiService.FOOTER_H - 140

        return f"""
        <g transform="translate({x:.2f},{y:.2f})">
            <rect x="0" y="0" width="210" height="115" rx="8" ry="8" fill="#FFFFFF" stroke="#CBD5E1"/>
            <text x="12" y="20" font-size="13" font-family="Arial" font-weight="bold" fill="#0F172A">LEGENDA</text>

            <circle cx="18" cy="40" r="4" fill="#111827"/>
            <text x="32" y="44" font-size="11" font-family="Arial" fill="#111827">Vértices do perímetro</text>

            <line x1="12" y1="62" x2="30" y2="62" stroke="#0F172A" stroke-width="3"/>
            <text x="36" y="66" font-size="11" font-family="Arial" fill="#111827">Perímetro do imóvel</text>

            <line x1="12" y1="84" x2="30" y2="84" stroke="#E5E7EB" stroke-width="2"/>
            <text x="36" y="88" font-size="11" font-family="Arial" fill="#111827">Malha de referência</text>

            <text x="12" y="106" font-size="11" font-family="Arial" fill="#111827">N = Norte</text>
        </g>
        """

    @staticmethod
    def _render_quadro_tecnico(
        size: int,
        area_m2: float,
        area_ha: float,
        perimetro_m: float,
        total_vertices: int,
        escala_aprox: float,
    ) -> str:
        size = float(size)

        x = size - CroquiService.RIGHT_INFO_W + 20
        y = CroquiService.HEADER_H + 110

        return f"""
        <g transform="translate({x:.2f},{y:.2f})">
            <rect x="0" y="0" width="210" height="165" rx="8" ry="8" fill="#FFFFFF" stroke="#CBD5E1"/>
            <text x="12" y="20" font-size="13" font-family="Arial" font-weight="bold" fill="#0F172A">QUADRO TÉCNICO</text>

            <text x="12" y="44" font-size="11" font-family="Arial" fill="#334155">Área (m²):</text>
            <text x="198" y="44" text-anchor="end" font-size="11" font-family="Arial" font-weight="bold" fill="#111827">{CroquiService._format_num(area_m2, 2)}</text>

            <text x="12" y="66" font-size="11" font-family="Arial" fill="#334155">Área (ha):</text>
            <text x="198" y="66" text-anchor="end" font-size="11" font-family="Arial" font-weight="bold" fill="#111827">{CroquiService._format_num(area_ha, 4)}</text>

            <text x="12" y="88" font-size="11" font-family="Arial" fill="#334155">Perímetro (m):</text>
            <text x="198" y="88" text-anchor="end" font-size="11" font-family="Arial" font-weight="bold" fill="#111827">{CroquiService._format_num(perimetro_m, 3)}</text>

            <text x="12" y="110" font-size="11" font-family="Arial" fill="#334155">Vértices:</text>
            <text x="198" y="110" text-anchor="end" font-size="11" font-family="Arial" font-weight="bold" fill="#111827">{total_vertices}</text>

            <text x="12" y="132" font-size="11" font-family="Arial" fill="#334155">Escala gráfica aprox.:</text>
            <text x="198" y="132" text-anchor="end" font-size="11" font-family="Arial" font-weight="bold" fill="#111827">1:{int(max(1, escala_aprox or 1))}</text>

            <text x="12" y="154" font-size="10" font-family="Arial" fill="#64748B">Croqui não substitui planta topográfica oficial.</text>
        </g>
        """

    @staticmethod
    def _render_segment_labels(
        norm: List[Tuple[float, float]],
        geojson: Any
    ) -> str:

        geojson_normalizado = CroquiService._normalizar_geojson(geojson)

        segmentos = GeometriaService.extract_segmentos(geojson_normalizado)

        labels = []

        for i, seg in enumerate(segmentos):
            if i >= len(norm) - 1:
                continue

            x1, y1 = norm[i]
            x2, y2 = norm[i + 1]

            mx, my = CroquiService._segment_midpoint((x1, y1), (x2, y2))

            dist = float(seg.get("distancia") or 0)
            az = float(seg.get("azimute_graus") or 0)

            texto = f"{CroquiService._format_num(dist, 2)} m | {az:.1f}°"

            labels.append(
                f'<text x="{mx:.2f}" y="{my - 10:.2f}" text-anchor="middle" '
                f'font-size="10" font-family="Arial" fill="#1E293B" '
                f'paint-order="stroke" stroke="#FFFFFF" stroke-width="3.5">'
                f'{texto}</text>'
            )

        return "\n".join(labels)
    
    

    @staticmethod
    def _render_vertices(norm: List[Tuple[float, float]]) -> str:
        labels = []

        for i, (x, y) in enumerate(norm[:-1], start=1):
            x = CroquiService._safe_float(x)
            y = CroquiService._safe_float(y)

            labels.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="4.2" fill="#111827" stroke="#FFFFFF" stroke-width="1.5"/>'
            )
            labels.append(
                f'<text x="{x + 8:.2f}" y="{y - 8:.2f}" font-size="12" font-family="Arial" font-weight="bold" '
                f'fill="#0F172A" paint-order="stroke" stroke="#FFFFFF" stroke-width="3">V{i}</text>'
            )

        return "\n".join(labels)

    @staticmethod
    def _render_confrontantes(
        confrontantes: List[Dict[str, Optional[str]]],
        norm: List[Tuple[float, float]],
    ) -> str:
        if not confrontantes:
            return ""

        linhas = []
        usados_por_lado: Dict[str, int] = {}

        # 🔥 alinhado com normalizador
        lado_para_segmento = {
            "NORTE": 0,
            "LESTE": 1,
            "SUL": 2,
            "OESTE": 3,
            "NORDESTE": 0,
            "SUDESTE": 1,
            "SUDOESTE": 2,
            "NOROESTE": 3,
        }

        total_segmentos = max(1, len(norm) - 1)

        for idx, c in enumerate(confrontantes, start=1):

            # 🔥 prioridade correta (normalizador primeiro)
            lado = str(
                c.get("lado_normalizado")
                or c.get("lado")
                or ""
            ).upper().strip()

            nome = str(c.get("nome") or "").strip()
            descricao = str(c.get("descricao") or "").strip()
            lote = str(c.get("lote") or "").strip()
            gleba = str(c.get("gleba") or "").strip()

            texto_principal = nome or descricao
            if not texto_principal:
                continue

            # =========================================================
            # COMPLEMENTO
            # =========================================================
            complemento = []

            if lote:
                complemento.append(f"Lote {lote}")

            if gleba:
                complemento.append(f"Gleba {gleba}")

            texto_final = texto_principal
            if complemento:
                texto_final += " • " + " • ".join(complemento)

            # =========================================================
            # POSICIONAMENTO
            # =========================================================
            segmento_index = lado_para_segmento.get(lado)

            if segmento_index is None:
                segmento_index = min(idx - 1, total_segmentos - 1)

            segmento_index = min(segmento_index, total_segmentos - 1)

            p1 = norm[segmento_index]
            p2 = norm[(segmento_index + 1) % len(norm)]

            mx, my = CroquiService._segment_midpoint(p1, p2)

            # =========================================================
            # CONTROLE DE SOBREPOSIÇÃO (MELHORADO)
            # =========================================================
            chave_lado = lado or f"AUTO_{segmento_index}"

            count = usados_por_lado.get(chave_lado, 0)
            usados_por_lado[chave_lado] = count + 1

            offset_y = 18 + (count * 16)  # 🔥 mais espaçamento
            anchor = "middle"

            linhas.append(
                f'<text x="{mx:.2f}" y="{my + offset_y:.2f}" text-anchor="{anchor}" '
                f'font-size="11" font-family="Arial" fill="#7C2D12" '
                f'paint-order="stroke" stroke="#FFFFFF" stroke-width="3">'
                f'{CroquiService._escape_xml(texto_final)}</text>'
            )

        return "\n".join(linhas)
    
    @staticmethod
    def gerar_svg(
        geojson: str | Dict[str, Any],
        confrontantes: Optional[List[Dict[str, Optional[str]]]] = None
    ) -> str:

        geojson_normalizado = CroquiService._normalizar_geojson(geojson)
        geom = CroquiService._parse_polygon(geojson_normalizado)

        coords = list(geom.exterior.coords)

        if len(coords) < 4:
            raise HTTPException(status_code=400, detail="Polígono inválido.")

        if coords[0] != coords[-1]:
            coords.append(coords[0])

        original_coords = [
            (
                CroquiService._safe_float(x),
                CroquiService._safe_float(y),
            )
            for x, y in coords
        ]

        norm, scale, meta = CroquiService._normalize_points(
            original_coords,
            CroquiService.SVG_SIZE,
        )

        size = CroquiService.SVG_SIZE

        poly_points = " ".join([f"{x:.2f},{y:.2f}" for x, y in norm])

        # =========================================================
        # MÉTRICAS TÉCNICAS (ALINHADAS COM GEOMETRIAS)
        # =========================================================
        area_m2 = CroquiService._polygon_area(original_coords)
        area_ha = area_m2 / 10000.0 if area_m2 > 0 else 0.0
        perimetro_m = CroquiService._polygon_perimeter(original_coords)

        try:
            epsg_utm, area_calc_ha, perimetro_calc_m = GeometriaService.calcular_area_perimetro(
                geojson=geojson_normalizado,
                epsg_origem=4326,
            )

            if area_calc_ha and area_calc_ha > 0:
                area_ha = CroquiService._safe_float(area_calc_ha)
                area_m2 = area_ha * 10000.0

            if perimetro_calc_m and perimetro_calc_m > 0:
                perimetro_m = CroquiService._safe_float(perimetro_calc_m)

        except Exception:
            area_m2 = CroquiService._safe_float(area_m2)
            area_ha = CroquiService._safe_float(area_ha)
            perimetro_m = CroquiService._safe_float(perimetro_m)

        total_vertices = max(0, len(norm) - 1)
        escala_aprox = (1 / scale) * 1000 if scale > 0 else 1

        titulo = CroquiService._render_header(size)
        grid = CroquiService._render_grid(size)
        footer = CroquiService._render_footer(size)
        north = CroquiService._render_north_arrow(size)
        escala = CroquiService._render_scale_bar(size, scale)
        legenda = CroquiService._render_legenda(size)
        quadro_tecnico = CroquiService._render_quadro_tecnico(
            size=size,
            area_m2=area_m2,
            area_ha=area_ha,
            perimetro_m=perimetro_m,
            total_vertices=total_vertices,
            escala_aprox=escala_aprox,
        )

        vertices_svg = CroquiService._render_vertices(norm)
        confrontantes_svg = CroquiService._render_confrontantes(confrontantes or [], norm)
        segmentos_svg = CroquiService._render_segment_labels(norm, geojson_normalizado)

        draw_bounds = CroquiService._drawing_bounds(size)

        svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">

  <rect x="0" y="0" width="{size}" height="{size}" fill="#FFFFFF"/>

  {titulo}

  {grid}

  <rect
    x="{draw_bounds['left']:.2f}"
    y="{draw_bounds['top']:.2f}"
    width="{draw_bounds['width']:.2f}"
    height="{draw_bounds['height']:.2f}"
    fill="none"
    stroke="#CBD5E1"
    stroke-width="1.2"
    rx="8"
    ry="8"
  />

  <polygon points="{poly_points}" fill="rgba(15, 23, 42, 0.04)" stroke="#0F172A" stroke-width="4.5"/>

  {segmentos_svg}

  {vertices_svg}

  {confrontantes_svg}

  {north}

  {quadro_tecnico}

  {legenda}

  {escala}

  {footer}

</svg>
"""
        return svg