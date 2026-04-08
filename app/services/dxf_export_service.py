from __future__ import annotations

import json
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

    @staticmethod
    def _safe_float(value: Any) -> float:
        try:
            return float(value)
        except Exception as exc:
            raise ValueError(f"Valor numérico inválido: {value}") from exc

    @staticmethod
    def _parse_polygon(geojson: str) -> Polygon:
        try:
            return GeometriaService._parse_polygon_geojson(geojson)
        except Exception as exc:
            raise ValueError("GeoJSON inválido para DXF") from exc

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

    @staticmethod
    def _setup_layers(doc: ezdxf.document.Drawing) -> None:
        DxfExportService._ensure_layer(
            doc=doc,
            name=DxfExportService.LAYER_PERIMETRO,
            color=3,
            linetype="CONTINUOUS",
            lineweight=35,
        )
        DxfExportService._ensure_layer(
            doc=doc,
            name=DxfExportService.LAYER_VERTICES,
            color=1,
            linetype="CONTINUOUS",
            lineweight=25,
        )
        DxfExportService._ensure_layer(
            doc=doc,
            name=DxfExportService.LAYER_ROTULOS_VERTICES,
            color=2,
            linetype="CONTINUOUS",
            lineweight=18,
        )
        DxfExportService._ensure_layer(
            doc=doc,
            name=DxfExportService.LAYER_SEGMENTOS,
            color=5,
            linetype="CONTINUOUS",
            lineweight=18,
        )
        DxfExportService._ensure_layer(
            doc=doc,
            name=DxfExportService.LAYER_NORTE,
            color=6,
            linetype="CONTINUOUS",
            lineweight=25,
        )
        DxfExportService._ensure_layer(
            doc=doc,
            name=DxfExportService.LAYER_CONFRONTANTES,
            color=30,
            linetype="DASHED",
            lineweight=18,
        )
        DxfExportService._ensure_layer(
            doc=doc,
            name=DxfExportService.LAYER_INFO,
            color=8,
            linetype="CONTINUOUS",
            lineweight=18,
        )

    @staticmethod
    def _calc_text_height(coords: List[Tuple[float, float]]) -> float:
        xs = [p[0] for p in coords]
        ys = [p[1] for p in coords]

        span_x = max(xs) - min(xs) if xs else 0.0
        span_y = max(ys) - min(ys) if ys else 0.0
        ref = max(span_x, span_y, 1.0)

        text_height = ref * 0.012

        if text_height < 1.5:
            return 1.5
        if text_height > 50:
            return 50.0
        return text_height

    @staticmethod
    def _calc_vertex_radius(text_height: float) -> float:
        radius = text_height * 0.35
        if radius < 0.3:
            return 0.3
        return radius

    @staticmethod
    def _calc_midpoint(
        p1: Tuple[float, float],
        p2: Tuple[float, float],
    ) -> Tuple[float, float]:
        return ((p1[0] + p2[0]) / 2.0, (p1[1] + p2[1]) / 2.0)

    @staticmethod
    def _calc_distance(
        p1: Tuple[float, float],
        p2: Tuple[float, float],
    ) -> float:
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        return (dx * dx + dy * dy) ** 0.5

    @staticmethod
    def _calc_north_arrow_position(
        coords: List[Tuple[float, float]],
        text_height: float,
    ) -> Tuple[float, float, float]:
        xs = [p[0] for p in coords]
        ys = [p[1] for p in coords]

        min_x = min(xs)
        max_x = max(xs)
        max_y = min(ys), max(ys)
        _, y_top = max_y

        span_x = max(xs) - min(xs)
        span_y = max(ys) - min(ys)
        ref = max(span_x, span_y, 1.0)

        x = min_x + (span_x * 0.90 if span_x > 0 else ref * 0.90)
        y = y_top + (ref * 0.08)
        size = text_height * 6.0

        return x, y, size

    @staticmethod
    def _add_north_arrow(
        msp: ezdxf.layouts.Modelspace,
        x: float,
        y: float,
        size: float,
        text_height: float,
    ) -> None:
        shaft_start = (x, y)
        shaft_end = (x, y + size)

        msp.add_line(
            shaft_start,
            shaft_end,
            dxfattribs={"layer": DxfExportService.LAYER_NORTE},
        )

        head_left = (x - (size * 0.18), y + size * 0.72)
        head_tip = (x, y + size)
        head_right = (x + (size * 0.18), y + size * 0.72)

        msp.add_lwpolyline(
            [head_left, head_tip, head_right],
            dxfattribs={"layer": DxfExportService.LAYER_NORTE},
        )

        msp.add_text(
            "N",
            dxfattribs={
                "layer": DxfExportService.LAYER_NORTE,
                "height": text_height * 1.2,
                "insert": (x + (size * 0.22), y + size * 0.82),
            },
        )

    @staticmethod
    def _add_info_box(
        msp: ezdxf.layouts.Modelspace,
        coords: List[Tuple[float, float]],
        text_height: float,
    ) -> None:
        xs = [p[0] for p in coords]
        ys = [p[1] for p in coords]

        min_x = min(xs)
        min_y = min(ys)
        span_y = max(ys) - min(ys)
        ref_y = span_y if span_y > 0 else 50.0

        x = min_x
        y = min_y - (ref_y * 0.12)

        msp.add_text(
            "DXF TÉCNICO - GEOINCRA",
            dxfattribs={
                "layer": DxfExportService.LAYER_INFO,
                "height": text_height,
                "insert": (x, y),
            },
        )

    # =========================================================
    # GERAR DXF PROFISSIONAL
    # =========================================================
    @staticmethod
    def gerar_dxf(geojson: str) -> ezdxf.document.Drawing:
        polygon = DxfExportService._parse_polygon(geojson)
        coords_raw: List[Tuple[float, float]] = list(polygon.exterior.coords)

        coords: List[Tuple[float, float]] = [
            (
                DxfExportService._safe_float(x),
                DxfExportService._safe_float(y),
            )
            for x, y in coords_raw
        ]

        doc = ezdxf.new(dxfversion="R2010")
        msp = doc.modelspace()

        DxfExportService._setup_layers(doc)

        text_height = DxfExportService._calc_text_height(coords)
        vertex_radius = DxfExportService._calc_vertex_radius(text_height)

        # =========================================================
        # PERÍMETRO
        # =========================================================
        msp.add_lwpolyline(
            coords,
            close=True,
            dxfattribs={
                "layer": DxfExportService.LAYER_PERIMETRO,
            },
        )

        # =========================================================
        # VÉRTICES + RÓTULOS
        # =========================================================
        for index, (x, y) in enumerate(coords[:-1], start=1):
            msp.add_circle(
                center=(x, y),
                radius=vertex_radius,
                dxfattribs={"layer": DxfExportService.LAYER_VERTICES},
            )

            msp.add_text(
                f"V{index}",
                dxfattribs={
                    "layer": DxfExportService.LAYER_ROTULOS_VERTICES,
                    "height": text_height,
                    "insert": (
                        x + (text_height * 0.60),
                        y + (text_height * 0.60),
                    ),
                },
            )

        # =========================================================
        # TEXTOS DOS SEGMENTOS (PROFISSIONAL)
        # =========================================================
        segmentos = GeometriaService.extract_segmentos(geojson)

        for index, seg in enumerate(segmentos):
            if index >= len(coords) - 1:
                continue

            p1 = coords[index]
            p2 = coords[index + 1]

            mx, my = DxfExportService._calc_midpoint(p1, p2)

            distancia = seg["distancia"]
            az = seg["azimute_graus"]

            texto = f"L{index + 1} = {distancia:.2f} m | Az: {az:.2f}°"

            msp.add_text(
                texto,
                dxfattribs={
                    "layer": DxfExportService.LAYER_SEGMENTOS,
                    "height": text_height * 0.85,
                    "insert": (
                        mx + (text_height * 0.30),
                        my + (text_height * 0.30),
                    ),
                },
            )

        # =========================================================
        # NORTE
        # =========================================================
        north_x, north_y, north_size = DxfExportService._calc_north_arrow_position(
            coords=coords,
            text_height=text_height,
        )
        DxfExportService._add_north_arrow(
            msp=msp,
            x=north_x,
            y=north_y,
            size=north_size,
            text_height=text_height,
        )

        # =========================================================
        # INFORMAÇÃO TÉCNICA
        # =========================================================
        DxfExportService._add_info_box(
            msp=msp,
            coords=coords,
            text_height=text_height,
        )

        return doc

    # =========================================================
    # SALVAR DXF
    # =========================================================
    @staticmethod
    def salvar_dxf(
        imovel_id: int,
        doc: ezdxf.document.Drawing,
        base_dir: str = "app/uploads/imoveis",
    ) -> str:
        ts = int(datetime.utcnow().timestamp())

        folder = os.path.join(base_dir, str(imovel_id), "cad")
        os.makedirs(folder, exist_ok=True)

        filename = f"perimetro_profissional_{ts}.dxf"
        path = os.path.join(folder, filename)

        doc.saveas(path)

        return path