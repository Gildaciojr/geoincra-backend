from __future__ import annotations

import os
from datetime import datetime
from typing import Any, List, Tuple

import ezdxf
from shapely.geometry import Polygon

from app.services.geometria_service import GeometriaService


class DxfExportService:
    # =========================================================
    # CONFIGURAÇÃO DE LAYERS (PADRÃO TOPOGRAFIA / CAD TÉCNICO)
    # =========================================================
    LAYER_PERIMETRO = "GEO_PERIMETRO"
    LAYER_VERTICES = "GEO_VERTICES"
    LAYER_ROTULOS_VERTICES = "GEO_VERTICES_TXT"
    LAYER_SEGMENTOS = "GEO_SEGMENTOS_TXT"
    LAYER_NORTE = "GEO_NORTE"
    LAYER_CONFRONTANTES = "GEO_CONFRONTANTES"
    LAYER_INFO = "GEO_INFO"

    # =========================================================
    # NORMALIZAÇÃO NUMÉRICA SEGURA
    # =========================================================
    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            v = float(value)

            if v != v:  # NaN
                raise ValueError("Valor NaN detectado")

            if v in (float("inf"), float("-inf")):
                raise ValueError("Valor infinito detectado")

            return v

        except Exception as exc:
            raise ValueError(f"Valor numérico inválido: {value}") from exc

    # =========================================================
    # PARSER DE POLÍGONO
    # =========================================================
    @staticmethod
    def _parse_polygon(geojson: str) -> Polygon:
        try:
            polygon = GeometriaService._parse_polygon_geojson(geojson)

            if not polygon.is_valid:
                raise ValueError("Geometria inválida (self-intersection ou erro topológico)")

            if polygon.is_empty:
                raise ValueError("Geometria vazia")

            return polygon

        except Exception as exc:
            raise ValueError("GeoJSON inválido para DXF") from exc

    # =========================================================
    # CRIAÇÃO / ATUALIZAÇÃO DE LAYER
    # =========================================================
    @staticmethod
    def _ensure_layer(
        doc: ezdxf.document.Drawing,
        name: str,
        color: int,
        linetype: str = "CONTINUOUS",
        lineweight: int = 25,
    ) -> None:
        if name in doc.layers:
            layer = doc.layers.get(name)

            layer.dxf.color = color
            layer.dxf.linetype = linetype
            layer.dxf.lineweight = lineweight

            return

        doc.layers.add(
            name=name,
            dxfattribs={
                "color": color,
                "linetype": linetype,
                "lineweight": lineweight,
            },
        )

    # =========================================================
    # SETUP COMPLETO DE LAYERS (PADRÃO CAD)
    # =========================================================
    @staticmethod
    def _setup_layers(doc: ezdxf.document.Drawing) -> None:
        # Perímetro principal
        DxfExportService._ensure_layer(
            doc=doc,
            name=DxfExportService.LAYER_PERIMETRO,
            color=3,  # verde
            linetype="CONTINUOUS",
            lineweight=35,
        )

        # Vértices (pontos)
        DxfExportService._ensure_layer(
            doc=doc,
            name=DxfExportService.LAYER_VERTICES,
            color=1,  # vermelho
            linetype="CONTINUOUS",
            lineweight=25,
        )

        # Texto dos vértices
        DxfExportService._ensure_layer(
            doc=doc,
            name=DxfExportService.LAYER_ROTULOS_VERTICES,
            color=2,  # amarelo
            linetype="CONTINUOUS",
            lineweight=18,
        )

        # Texto de segmentos
        DxfExportService._ensure_layer(
            doc=doc,
            name=DxfExportService.LAYER_SEGMENTOS,
            color=5,  # azul
            linetype="CONTINUOUS",
            lineweight=18,
        )

        # Norte
        DxfExportService._ensure_layer(
            doc=doc,
            name=DxfExportService.LAYER_NORTE,
            color=6,
            linetype="CONTINUOUS",
            lineweight=25,
        )

        # Confrontantes
        DxfExportService._ensure_layer(
            doc=doc,
            name=DxfExportService.LAYER_CONFRONTANTES,
            color=30,
            linetype="DASHED",
            lineweight=18,
        )

        # Informações gerais
        DxfExportService._ensure_layer(
            doc=doc,
            name=DxfExportService.LAYER_INFO,
            color=8,
            linetype="CONTINUOUS",
            lineweight=18,
        )

    # =========================================================
    # CÁLCULO DE ESCALA DE TEXTO (INTELIGENTE)
    # =========================================================
    @staticmethod
    def _calc_text_height(coords: List[Tuple[float, float]]) -> float:
        if not coords:
            return 2.5

        try:
            xs = [DxfExportService._safe_float(p[0]) for p in coords]
            ys = [DxfExportService._safe_float(p[1]) for p in coords]

            if not xs or not ys:
                return 2.5

            min_x = min(xs)
            max_x = max(xs)
            min_y = min(ys)
            max_y = max(ys)

            span_x = DxfExportService._safe_float(max_x - min_x)
            span_y = DxfExportService._safe_float(max_y - min_y)

            ref = max(span_x, span_y, 1.0)

            # Escala proporcional (ajustada para leitura técnica)
            text_height = ref * 0.012

            # Limites técnicos CAD
            if text_height < 1.5:
                return 1.5

            if text_height > 50:
                return 50.0

            return text_height

        except Exception:
            return 2.5

    @staticmethod
    def _calc_vertex_radius(text_height: float) -> float:
        text_height = DxfExportService._safe_float(text_height)

        radius = text_height * 0.35

        if radius < 0.3:
            return 0.3

        if radius > 20:
            return 20.0

        return radius

    @staticmethod
    def _calc_midpoint(
        p1: Tuple[float, float],
        p2: Tuple[float, float],
    ) -> Tuple[float, float]:
        x1 = DxfExportService._safe_float(p1[0])
        y1 = DxfExportService._safe_float(p1[1])
        x2 = DxfExportService._safe_float(p2[0])
        y2 = DxfExportService._safe_float(p2[1])

        return (
            (x1 + x2) / 2.0,
            (y1 + y2) / 2.0,
        )

    @staticmethod
    def _calc_distance(
        p1: Tuple[float, float],
        p2: Tuple[float, float],
    ) -> float:
        x1 = DxfExportService._safe_float(p1[0])
        y1 = DxfExportService._safe_float(p1[1])
        x2 = DxfExportService._safe_float(p2[0])
        y2 = DxfExportService._safe_float(p2[1])

        dx = x2 - x1
        dy = y2 - y1

        return (dx * dx + dy * dy) ** 0.5

    @staticmethod
    def _calc_north_arrow_position(
        coords: List[Tuple[float, float]],
        text_height: float,
    ) -> Tuple[float, float, float]:
        if not coords:
            raise ValueError("Coordenadas ausentes para cálculo da seta norte")

        xs = [DxfExportService._safe_float(p[0]) for p in coords]
        ys = [DxfExportService._safe_float(p[1]) for p in coords]

        min_x = min(xs)
        max_x = max(xs)
        min_y = min(ys)
        max_y = max(ys)

        span_x = DxfExportService._safe_float(max_x - min_x)
        span_y = DxfExportService._safe_float(max_y - min_y)

        ref = max(span_x, span_y, 1.0)

        # posiciona no quadrante superior direito, fora da poligonal
        x = min_x + (span_x * 0.90 if span_x > 0 else ref * 0.90)
        y = max_y + (ref * 0.08)

        size = DxfExportService._safe_float(text_height) * 6.0

        if size < 5.0:
            size = 5.0

        return x, y, size
    
    @staticmethod
    def _add_north_arrow(
        msp: ezdxf.layouts.Modelspace,
        x: float,
        y: float,
        size: float,
        text_height: float,
    ) -> None:
        try:
            x = DxfExportService._safe_float(x)
            y = DxfExportService._safe_float(y)
            size = max(5.0, DxfExportService._safe_float(size))
            text_height = DxfExportService._safe_float(text_height)

            shaft_start = (x, y)
            shaft_end = (x, y + size)

            msp.add_line(
                shaft_start,
                shaft_end,
                dxfattribs={
                    "layer": DxfExportService.LAYER_NORTE,
                },
            )

            head_left = (
                x - (size * 0.18),
                y + (size * 0.72),
            )
            head_tip = (
                x,
                y + size,
            )
            head_right = (
                x + (size * 0.18),
                y + (size * 0.72),
            )

            msp.add_lwpolyline(
                [head_left, head_tip, head_right],
                dxfattribs={
                    "layer": DxfExportService.LAYER_NORTE,
                },
            )

            msp.add_text(
                "N",
                dxfattribs={
                    "layer": DxfExportService.LAYER_NORTE,
                    "height": text_height * 1.2,
                    "insert": (
                        x + (size * 0.22),
                        y + (size * 0.82),
                    ),
                },
            )

        except Exception:
            # não quebra o DXF
            pass

    @staticmethod
    def _add_info_box(
        msp: ezdxf.layouts.Modelspace,
        coords: List[Tuple[float, float]],
        text_height: float,
    ) -> None:
        if not coords:
            return

        try:
            xs = [DxfExportService._safe_float(p[0]) for p in coords]
            ys = [DxfExportService._safe_float(p[1]) for p in coords]

            min_x = min(xs)
            min_y = min(ys)
            max_y = max(ys)

            span_y = max_y - min_y
            ref_y = span_y if span_y > 0 else 50.0

            offset_y = ref_y * 0.15

            x = min_x
            y = min_y - offset_y

            texto = (
                "GEOINCRA\n"
                "DXF TÉCNICO GERADO AUTOMATICAMENTE\n"
                f"DATA: {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC"
            )

            msp.add_mtext(
                texto,
                dxfattribs={
                    "layer": DxfExportService.LAYER_INFO,
                    "char_height": text_height,
                    "insert": (x, y),
                },
            )

        except Exception:
            pass

    # =========================================================
    # 🔥 QUADRO TÉCNICO (PADRÃO SIGEF)
    # =========================================================
    @staticmethod
    def _add_quadro_tecnico(
        msp: ezdxf.layouts.Modelspace,
        coords: List[Tuple[float, float]],
        text_height: float,
        area_ha: float,
        perimetro_m: float,
        epsg_origem: int | None = None,
        epsg_utm: int | None = None,
    ) -> None:
        if not coords:
            return

        try:
            xs = [DxfExportService._safe_float(p[0]) for p in coords]
            ys = [DxfExportService._safe_float(p[1]) for p in coords]

            min_x = min(xs)
            max_x = max(xs)
            max_y = max(ys)

            span_x = max_x - min_x
            span_y = max(ys) - min(ys)
            ref = max(span_x, span_y, 1.0)

            x = min_x + (span_x * 0.02 if span_x > 0 else ref * 0.02)
            y = max_y + (ref * 0.12)

            area_ha = DxfExportService._safe_float(area_ha or 0.0)
            perimetro_m = DxfExportService._safe_float(perimetro_m or 0.0)

            texto = (
                "QUADRO TÉCNICO\n"
                f"ÁREA: {area_ha:.4f} ha\n"
                f"PERÍMETRO: {perimetro_m:.3f} m\n"
                f"VÉRTICES: {max(0, len(coords) - 1)}\n"
                f"EPSG ORIGEM: {epsg_origem if epsg_origem else 'N/A'}\n"
                f"EPSG UTM: {epsg_utm if epsg_utm else 'N/A'}\n"
                f"EMISSÃO: {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC"
            )

            msp.add_mtext(
                texto,
                dxfattribs={
                    "layer": DxfExportService.LAYER_INFO,
                    "char_height": text_height,
                    "insert": (x, y),
                },
            )

        except Exception:
            pass

    # =========================================================
    # 🔥 TABELA DE COORDENADAS (ESTILO SIGEF)
    # =========================================================
    @staticmethod
    def _add_tabela_coordenadas(
        msp: ezdxf.layouts.Modelspace,
        coords: List[Tuple[float, float]],
        text_height: float,
        segmentos: List[dict[str, Any]] | None = None,
    ) -> None:
        if not coords:
            return

        def _format_azimute_dms_local(az: float) -> str:
            az = DxfExportService._safe_float(az) % 360

            graus = int(az)
            minutos_float = (az - graus) * 60
            minutos = int(minutos_float)
            segundos = (minutos_float - minutos) * 60

            return f"{graus:03d}°{minutos:02d}'{segundos:05.2f}\""

        try:
            xs = [DxfExportService._safe_float(p[0]) for p in coords]
            ys = [DxfExportService._safe_float(p[1]) for p in coords]

            min_x = min(xs)
            min_y = min(ys)
            max_y = max(ys)

            span_y = max_y - min_y
            ref_y = span_y if span_y > 0 else 50.0

            x = min_x
            y = min_y - (ref_y * 0.35)

            row_h = text_height * 1.35

            header = "VÉRTICE        X                 Y                 DISTÂNCIA         AZIMUTE"

            msp.add_text(
                header,
                dxfattribs={
                    "layer": DxfExportService.LAYER_INFO,
                    "height": text_height,
                    "insert": (x, y),
                },
            )

            y_atual = y - row_h
            total_vertices = max(0, len(coords) - 1)

            for i in range(total_vertices):
                vx = DxfExportService._safe_float(coords[i][0])
                vy = DxfExportService._safe_float(coords[i][1])

                distancia_str = "-"
                azimute_str = "-"

                if segmentos and i < len(segmentos):
                    try:
                        distancia_val = DxfExportService._safe_float(
                            segmentos[i].get("distancia", 0)
                        )
                        azimute_val = DxfExportService._safe_float(
                            segmentos[i].get("azimute_graus", 0)
                        )

                        distancia_str = f"{distancia_val:.3f}"
                        azimute_str = _format_azimute_dms_local(azimute_val)
                    except Exception:
                        pass

                linha = (
                    f"V{i + 1:<3}"
                    f"    {vx:>14.3f}"
                    f"    {vy:>14.3f}"
                    f"    {distancia_str:>12}"
                    f"    {azimute_str:>16}"
                )

                msp.add_text(
                    linha,
                    dxfattribs={
                        "layer": DxfExportService.LAYER_INFO,
                        "height": text_height * 0.90,
                        "insert": (x, y_atual),
                    },
                )

                y_atual -= row_h

        except Exception:
            pass

    # =========================================================
    # FORMATADOR DE AZIMUTE (DMS)
    # =========================================================
    @staticmethod
    def _format_azimute_dms(az: float) -> str:
        az = DxfExportService._safe_float(az) % 360

        graus = int(az)
        minutos_float = (az - graus) * 60
        minutos = int(minutos_float)
        segundos = (minutos_float - minutos) * 60

        return f"{graus:03d}°{minutos:02d}'{segundos:05.2f}\""

    # =========================================================
    # RENDERIZADOR INTERNO (BASE ÚNICA)
    # =========================================================
    @staticmethod
    def _render_dxf_document(
        coords: List[Tuple[float, float]],
        segmentos: List[dict[str, Any]],
        area_ha: float,
        perimetro_m: float,
        epsg_origem: int | None = None,
        epsg_utm: int | None = None,
    ) -> ezdxf.document.Drawing:
        if not coords or len(coords) < 4:
            raise ValueError("Coordenadas insuficientes para geração do DXF")

        import math

        doc = ezdxf.new(dxfversion="R2010")
        msp = doc.modelspace()

        DxfExportService._setup_layers(doc)

        text_height = DxfExportService._calc_text_height(coords)
        vertex_radius = DxfExportService._calc_vertex_radius(text_height)

        # =========================================================
        # PERÍMETRO (POLÍGONO PRINCIPAL)
        # =========================================================
        msp.add_lwpolyline(
            coords,
            close=True,
            dxfattribs={
                "layer": DxfExportService.LAYER_PERIMETRO,
            },
        )

        # =========================================================
        # VÉRTICES + RÓTULOS (PADRÃO SIGEF)
        # =========================================================
        for index, (x, y) in enumerate(coords[:-1], start=1):
            x = DxfExportService._safe_float(x)
            y = DxfExportService._safe_float(y)

            msp.add_circle(
                center=(x, y),
                radius=vertex_radius,
                dxfattribs={
                    "layer": DxfExportService.LAYER_VERTICES,
                },
            )

            offset = text_height * 0.60

            msp.add_text(
                f"V{index}",
                dxfattribs={
                    "layer": DxfExportService.LAYER_ROTULOS_VERTICES,
                    "height": text_height,
                    "insert": (
                        x + offset,
                        y + offset,
                    ),
                },
            )

        # =========================================================
        # TEXTOS DOS SEGMENTOS + CONFRONTANTES
        # =========================================================
        for index, seg in enumerate(segmentos):
            if index >= len(coords) - 1:
                continue

            try:
                p1 = coords[index]
                p2 = coords[index + 1]

                mx, my = DxfExportService._calc_midpoint(p1, p2)

                distancia = DxfExportService._safe_float(seg.get("distancia", 0))
                az = DxfExportService._safe_float(
                    seg.get("azimute_graus", seg.get("azimute", 0))
                )

                az_dms = DxfExportService._format_azimute_dms(az)

                texto_segmento = f"L{index + 1} = {distancia:.2f} m | Az: {az_dms}"

                # =========================================================
                # DIREÇÃO DO SEGMENTO
                # =========================================================
                dx = DxfExportService._safe_float(p2[0] - p1[0])
                dy = DxfExportService._safe_float(p2[1] - p1[1])

                angle = 0.0
                if dx != 0 or dy != 0:
                    angle = math.degrees(math.atan2(dy, dx))

                # normal perpendicular
                nx = -dy
                ny = dx

                norm = (nx * nx + ny * ny) ** 0.5
                if norm != 0:
                    nx /= norm
                    ny /= norm

                # =========================================================
                # TEXTO DO SEGMENTO
                # =========================================================
                offset_segmento = text_height * 0.35

                insert_x_seg = mx + (nx * offset_segmento)
                insert_y_seg = my + (ny * offset_segmento)

                msp.add_text(
                    texto_segmento,
                    dxfattribs={
                        "layer": DxfExportService.LAYER_SEGMENTOS,
                        "height": text_height * 0.85,
                        "rotation": angle,
                        "insert": (
                            insert_x_seg,
                            insert_y_seg,
                        ),
                    },
                )

                # =========================================================
                # 🔥 CONFRONTANTE (NOVO - INTEGRADO)
                # =========================================================
                confrontante = seg.get("confrontante")

                if confrontante:
                    offset_conf = text_height * 1.2

                    insert_x_conf = mx + (nx * offset_conf)
                    insert_y_conf = my + (ny * offset_conf)

                    texto_conf = f"CONF.: {str(confrontante).upper()}"

                    msp.add_text(
                        texto_conf,
                        dxfattribs={
                            "layer": DxfExportService.LAYER_CONFRONTANTES,
                            "height": text_height * 0.95,
                            "rotation": angle,
                            "insert": (
                                insert_x_conf,
                                insert_y_conf,
                            ),
                        },
                    )

            except Exception:
                continue

        # =========================================================
        # NORTE
        # =========================================================
        try:
            north_x, north_y, north_size = (
                DxfExportService._calc_north_arrow_position(
                    coords=coords,
                    text_height=text_height,
                )
            )

            DxfExportService._add_north_arrow(
                msp=msp,
                x=north_x,
                y=north_y,
                size=north_size,
                text_height=text_height,
            )
        except Exception:
            pass

        # =========================================================
        # QUADRO TÉCNICO (POSIÇÃO SUPERIOR)
        # =========================================================
        try:
            DxfExportService._add_quadro_tecnico(
                msp=msp,
                coords=coords,
                text_height=text_height,
                area_ha=DxfExportService._safe_float(area_ha),
                perimetro_m=DxfExportService._safe_float(perimetro_m),
                epsg_origem=epsg_origem,
                epsg_utm=epsg_utm,
            )
        except Exception:
            pass

        # =========================================================
        # INFORMAÇÃO TÉCNICA BASE (RODAPÉ)
        # =========================================================
        try:
            DxfExportService._add_info_box(
                msp=msp,
                coords=coords,
                text_height=text_height,
            )
        except Exception:
            pass

        # =========================================================
        # TABELA DE COORDENADAS (ABAIXO DO POLÍGONO)
        # =========================================================
        try:
            DxfExportService._add_tabela_coordenadas(
                msp=msp,
                coords=coords,
                text_height=text_height,
                segmentos=segmentos,
            )
        except Exception:
            pass

        # =========================================================
        # FINALIZAÇÃO
        # =========================================================
        return doc

    # =========================================================
    # GERAR DXF PROFISSIONAL (VIA GEOJSON)
    # =========================================================
    @staticmethod
    def gerar_dxf(geojson: str) -> ezdxf.document.Drawing:
        polygon = DxfExportService._parse_polygon(geojson)

        coords_raw: List[Tuple[float, float]] = list(polygon.exterior.coords)

        if len(coords_raw) < 4:
            raise ValueError("Polígono inválido para geração de DXF")

        coords: List[Tuple[float, float]] = [
            (
                DxfExportService._safe_float(x),
                DxfExportService._safe_float(y),
            )
            for x, y in coords_raw
        ]

        epsg_origem = 4326
        epsg_utm = None
        area_ha = 0.0
        perimetro_m = 0.0

        try:
            epsg_utm, area_ha_calc, perimetro_m_calc = GeometriaService.calcular_area_perimetro(
                geojson=geojson,
                epsg_origem=epsg_origem,
            )

            area_ha = DxfExportService._safe_float(area_ha_calc)
            perimetro_m = DxfExportService._safe_float(perimetro_m_calc)

        except Exception:
            try:
                area_ha = DxfExportService._safe_float(polygon.area / 10000.0)
            except Exception:
                area_ha = 0.0

            try:
                perimetro_m = DxfExportService._safe_float(polygon.length)
            except Exception:
                perimetro_m = 0.0

        try:
            segmentos = GeometriaService.extract_segmentos(geojson)
        except Exception:
            segmentos = []

        return DxfExportService._render_dxf_document(
            coords=coords,
            segmentos=segmentos,
            area_ha=area_ha,
            perimetro_m=perimetro_m,
            epsg_origem=epsg_origem,
            epsg_utm=epsg_utm,
        )

    # =========================================================
    # GERAR DXF PROFISSIONAL (VIA BANCO)
    # =========================================================
    @staticmethod
    def gerar_dxf_por_geometria_id(
        db: Any,
        geometria_id: int,
    ) -> ezdxf.document.Drawing:
        from app.models.geometria import Geometria

        geometria = (
            db.query(Geometria)
            .filter(Geometria.id == geometria_id)
            .first()
        )

        if not geometria:
            raise ValueError("Geometria não encontrada")

        coords: List[Tuple[float, float]] = []
        segmentos_render: List[dict[str, Any]] = []

        # =========================================================
        # COORDENADAS VIA BANCO (PRIORIDADE)
        # =========================================================
        if getattr(geometria, "vertices", None):
            vertices_ordenados = sorted(
                geometria.vertices,
                key=lambda v: (v.indice or 0, v.id or 0)
            )

            for v in vertices_ordenados:
                coords.append(
                    (
                        DxfExportService._safe_float(v.x),
                        DxfExportService._safe_float(v.y),
                    )
                )

            if coords and coords[0] != coords[-1]:
                coords.append(coords[0])

        # =========================================================
        # FALLBACK: GEOJSON
        # =========================================================
        if not coords:
            polygon = DxfExportService._parse_polygon(geometria.geojson)
            coords_raw = list(polygon.exterior.coords)

            if len(coords_raw) < 4:
                raise ValueError("Polígono inválido para geração de DXF")

            coords = [
                (
                    DxfExportService._safe_float(x),
                    DxfExportService._safe_float(y),
                )
                for x, y in coords_raw
            ]

        # =========================================================
        # SEGMENTOS VIA BANCO (PRIORIDADE)
        # =========================================================
        if getattr(geometria, "segmentos", None):
            try:
                segmentos_ordenados = sorted(
                    geometria.segmentos,
                    key=lambda s: (s.indice or 0, s.id or 0),
                )

                for seg in segmentos_ordenados:
                    try:
                        distancia = DxfExportService._safe_float(
                            getattr(seg, "distancia", 0)
                        )

                        azimute = DxfExportService._safe_float(
                            getattr(seg, "azimute", 0)
                        )

                        # =========================================================
                        # 🔥 CONFRONTANTE (FONTE REAL + FALLBACK CONTROLADO)
                        # =========================================================
                        confrontante_nome = None

                        try:
                            # 1. RELACIONAMENTO DIRETO (PRIORIDADE MÁXIMA)
                            if getattr(seg, "confrontante", None):
                                confrontante_nome = getattr(
                                    seg.confrontante,
                                    "nome",
                                    None,
                                )

                            # 2. CAMPOS DIRETOS DO SEGMENTO
                            if not confrontante_nome:
                                confrontante_nome = (
                                    getattr(seg, "confrontante_nome", None)
                                    or getattr(seg, "nome_confrontante", None)
                                )

                            # 3. NORMALIZAÇÃO FINAL
                            if confrontante_nome:
                                confrontante_nome = str(confrontante_nome).strip().upper()

                            # 4. 🔥 FALLBACK POR LADO (EVITA DXF "MUDO")
                            if not confrontante_nome:
                                lado = getattr(seg, "lado", None)

                                if lado:
                                    confrontante_nome = f"LADO {str(lado).upper()}"

                        except Exception:
                            confrontante_nome = None

                        segmentos_render.append(
                            {
                                "indice": getattr(seg, "indice", None),
                                "distancia": distancia,
                                "azimute_graus": azimute,
                                "confrontante": confrontante_nome,
                            }
                        )

                    except Exception:
                        continue

            except Exception:
                pass

        # =========================================================
        # FALLBACK: EXTRAÇÃO VIA GEOJSON
        # =========================================================
        if not segmentos_render:
            try:
                segmentos_extraidos = GeometriaService.extract_segmentos(
                    geometria.geojson
                )

                for seg in segmentos_extraidos:
                    try:
                        segmentos_render.append(
                            {
                                "indice": seg.get("indice"),
                                "distancia": DxfExportService._safe_float(
                                    seg.get("distancia", 0)
                                ),
                                "azimute_graus": DxfExportService._safe_float(
                                    seg.get("azimute_graus", 0)
                                ),
                                # fallback NÃO terá confrontante
                                "confrontante": (
                                    seg.get("confrontante")
                                    or seg.get("confrontante_nome")
                                    or None
                                ),
                            }
                        )
                    except Exception:
                        continue

            except Exception:
                segmentos_render = []

        # =========================================================
        # MÉTRICAS
        # =========================================================
        epsg_origem = getattr(geometria, "epsg_origem", None)
        epsg_utm = getattr(geometria, "epsg_utm", None)

        try:
            epsg_origem = int(epsg_origem) if epsg_origem is not None else None
        except Exception:
            epsg_origem = None

        try:
            epsg_utm = int(epsg_utm) if epsg_utm is not None else None
        except Exception:
            epsg_utm = None

        try:
            area_ha = DxfExportService._safe_float(
                getattr(geometria, "area_hectares", 0) or 0
            )
        except Exception:
            area_ha = 0.0

        try:
            perimetro_m = DxfExportService._safe_float(
                getattr(geometria, "perimetro_m", 0) or 0
            )
        except Exception:
            perimetro_m = 0.0

        # =========================================================
        # FALLBACK DE MÉTRICAS VIA GEOJSON
        # =========================================================
        if area_ha <= 0 or perimetro_m <= 0:
            try:
                geojson_base = getattr(geometria, "geojson", None)

                if not geojson_base:
                    raise ValueError("GeoJSON ausente para cálculo complementar")

                epsg_utm_calc, area_ha_calc, perimetro_m_calc = (
                    GeometriaService.calcular_area_perimetro(
                        geojson=geojson_base,
                        epsg_origem=epsg_origem or 4326,
                    )
                )

                if area_ha <= 0:
                    try:
                        area_ha = DxfExportService._safe_float(area_ha_calc)
                    except Exception:
                        area_ha = 0.0

                if perimetro_m <= 0:
                    try:
                        perimetro_m = DxfExportService._safe_float(perimetro_m_calc)
                    except Exception:
                        perimetro_m = 0.0

                if not epsg_utm and epsg_utm_calc:
                    try:
                        epsg_utm = int(epsg_utm_calc)
                    except Exception:
                        epsg_utm = None

            except Exception:
                pass

        # =========================================================
        # RENDER FINAL DO DXF
        # =========================================================
        return DxfExportService._render_dxf_document(
            coords=coords,
            segmentos=segmentos_render,
            area_ha=area_ha,
            perimetro_m=perimetro_m,
            epsg_origem=epsg_origem,
            epsg_utm=epsg_utm,
        )

    # =========================================================
    # SALVAR DXF (ROBUSTO)
    # =========================================================
    @staticmethod
    def salvar_dxf(
        imovel_id: int,
        doc: ezdxf.document.Drawing,
        base_dir: str = "app/uploads/imoveis",
    ) -> str:
        if not doc:
            raise ValueError("Documento DXF inválido")

        ts = int(datetime.utcnow().timestamp())
        folder = os.path.join(base_dir, str(imovel_id), "cad")

        try:
            os.makedirs(folder, exist_ok=True)
        except Exception as exc:
            raise Exception(f"Erro ao criar diretório DXF: {str(exc)}") from exc

        filename = f"perimetro_profissional_{ts}.dxf"
        path = os.path.join(folder, filename)

        try:
            doc.saveas(path)
        except Exception as exc:
            raise Exception(f"Erro ao salvar DXF: {str(exc)}") from exc

        return path