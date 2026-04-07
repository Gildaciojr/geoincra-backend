# app/services/croqui_service.py

import json
from typing import List, Tuple, Optional, Dict
from fastapi import HTTPException
from shapely.geometry import shape, Polygon


class CroquiService:

    @staticmethod
    def _normalize_points(coords: List[Tuple[float, float]], size: int = 900, pad: int = 80):
        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]

        minx, maxx = min(xs), max(xs)
        miny, maxy = min(ys), max(ys)

        w = (maxx - minx) if (maxx - minx) != 0 else 1.0
        h = (maxy - miny) if (maxy - miny) != 0 else 1.0

        scale = min((size - 2 * pad) / w, (size - 2 * pad) / h)

        norm = []
        for x, y in coords:
            nx = (x - minx) * scale + pad
            ny = (maxy - y) * scale + pad
            norm.append((nx, ny))

        return norm, size, scale

    @staticmethod
    def _render_confrontantes(
        confrontantes: List[Dict[str, Optional[str]]],
        size: int
    ) -> str:

        if not confrontantes:
            return ""

        linhas = []

        posicoes = {
            "NORTE": (size / 2, 40),
            "SUL": (size / 2, size - 30),
            "LESTE": (size - 30, size / 2),
            "OESTE": (30, size / 2),
        }

        for c in confrontantes:
            lado = (c.get("lado") or "").upper()
            nome = c.get("nome") or ""

            if not nome:
                continue

            pos = posicoes.get(lado)

            if not pos:
                continue

            x, y = pos

            anchor = "middle"
            if lado == "LESTE":
                anchor = "end"
            elif lado == "OESTE":
                anchor = "start"

            linhas.append(
                f'<text x="{x:.2f}" y="{y:.2f}" '
                f'font-size="12" font-family="Arial" fill="#111" text-anchor="{anchor}">'
                f'{lado}: {nome}</text>'
            )

        return "\n".join(linhas)

    @staticmethod
    def _render_escala(size: int) -> str:
        return f"""
        <g transform="translate(60,{size-60})">
            <line x1="0" y1="0" x2="200" y2="0" stroke="#000" stroke-width="2"/>
            <line x1="0" y1="-5" x2="0" y2="5" stroke="#000"/>
            <line x1="100" y1="-5" x2="100" y2="5" stroke="#000"/>
            <line x1="200" y1="-5" x2="200" y2="5" stroke="#000"/>
            <text x="0" y="20" font-size="10">0</text>
            <text x="90" y="20" font-size="10">50</text>
            <text x="180" y="20" font-size="10">100 m</text>
        </g>
        """

    @staticmethod
    def _render_legenda(size: int) -> str:
        return f"""
        <g transform="translate({size-260},{size-140})">
            <rect x="0" y="0" width="220" height="100" fill="white" stroke="#000"/>
            <text x="10" y="15" font-size="12" font-family="Arial" font-weight="bold">LEGENDA</text>

            <circle cx="15" cy="35" r="3" fill="#000"/>
            <text x="30" y="38" font-size="11">Vértices</text>

            <line x1="10" y1="55" x2="30" y2="55" stroke="#0f172a" stroke-width="3"/>
            <text x="35" y="58" font-size="11">Perímetro</text>

            <text x="10" y="80" font-size="11">N: Norte</text>
        </g>
        """

    @staticmethod
    def _render_titulo(size: int) -> str:
        return f"""
        <text x="{size/2}" y="30" text-anchor="middle"
              font-size="16" font-family="Arial" font-weight="bold">
              CROQUI DO IMÓVEL
        </text>
        """

    @staticmethod
    def gerar_svg(
        geojson: str,
        confrontantes: Optional[List[Dict[str, Optional[str]]]] = None
    ) -> str:

        try:
            geom = shape(json.loads(geojson))
        except Exception as exc:
            raise HTTPException(status_code=400, detail="GeoJSON inválido.") from exc

        if not isinstance(geom, Polygon):
            raise HTTPException(status_code=400, detail="Geometria deve ser POLYGON.")

        if geom.is_empty:
            raise HTTPException(status_code=400, detail="Geometria vazia.")

        if not geom.is_valid:
            geom = geom.buffer(0)

        if geom.is_empty or not geom.is_valid:
            raise HTTPException(status_code=400, detail="Geometria inválida para croqui.")

        coords = list(geom.exterior.coords)

        if len(coords) < 4:
            raise HTTPException(status_code=400, detail="Polígono inválido.")

        if coords[0] != coords[-1]:
            coords.append(coords[0])

        # NORMALIZAÇÃO
        norm, size, scale = CroquiService._normalize_points(
            [(float(x), float(y)) for x, y in coords]
        )

        poly_points = " ".join([f"{x:.2f},{y:.2f}" for x, y in norm])

        # VÉRTICES
        labels = []
        for i, (x, y) in enumerate(norm[:-1], start=1):
            labels.append(
                f'<text x="{x+6:.2f}" y="{y-6:.2f}" font-size="13" font-family="Arial">V{i}</text>'
            )
            labels.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="#000"/>'
            )

        # CONFRONTANTES
        confrontantes_svg = CroquiService._render_confrontantes(
            confrontantes or [],
            size
        )

        # NORTE
        north = f"""
        <g transform="translate({size-100},80)">
          <line x1="0" y1="40" x2="0" y2="0" stroke="#000" stroke-width="3"/>
          <polygon points="0,-12 -10,6 10,6" fill="#000"/>
          <text x="14" y="6" font-size="14">N</text>
        </g>
        """

        # NOVOS ELEMENTOS
        titulo = CroquiService._render_titulo(size)
        escala = CroquiService._render_escala(size)
        legenda = CroquiService._render_legenda(size)

        svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">

  <rect x="0" y="0" width="{size}" height="{size}" fill="white"/>

  {titulo}

  <polygon points="{poly_points}" fill="none" stroke="#0f172a" stroke-width="3"/>

  {north}

  {"".join(labels)}

  {confrontantes_svg}

  {escala}

  {legenda}

</svg>
"""

        return svg