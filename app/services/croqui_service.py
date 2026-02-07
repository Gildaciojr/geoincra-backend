# app/services/croqui_service.py

import json
from typing import List, Tuple
from fastapi import HTTPException
from shapely.geometry import shape, Polygon


class CroquiService:
    @staticmethod
    def _normalize_points(coords: List[Tuple[float, float]], size: int = 900, pad: int = 40):
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

        return norm, size

    @staticmethod
    def gerar_svg(geojson: str) -> str:
        try:
            geom = shape(json.loads(geojson))
        except Exception as exc:
            raise HTTPException(status_code=400, detail="GeoJSON inválido.") from exc

        if not isinstance(geom, Polygon):
            raise HTTPException(status_code=400, detail="Geometria deve ser POLYGON.")

        coords = list(geom.exterior.coords)
        if coords[0] != coords[-1]:
            coords.append(coords[0])

        # Para croqui “visual”
        norm, size = CroquiService._normalize_points([(float(x), float(y)) for x, y in coords])

        poly_points = " ".join([f"{x:.2f},{y:.2f}" for x, y in norm])

        # labels
        labels = []
        for i, (x, y) in enumerate(norm[:-1], start=1):
            labels.append(
                f'<text x="{x+6:.2f}" y="{y-6:.2f}" font-size="14" font-family="Arial" fill="#111">'
                f'V{i}</text>'
            )
            labels.append(
                f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.5" fill="#111" />'
            )

        # seta norte simples
        north = f"""
        <g transform="translate({size-90},60)">
          <line x1="0" y1="40" x2="0" y2="0" stroke="#111" stroke-width="3"/>
          <polygon points="0,-12 -10,6 10,6" fill="#111"/>
          <text x="14" y="6" font-size="16" font-family="Arial" fill="#111">N</text>
        </g>
        """

        svg = f"""<?xml version="1.0" encoding="UTF-8"?>
<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" xmlns="http://www.w3.org/2000/svg">
  <rect x="0" y="0" width="{size}" height="{size}" fill="white"/>
  <polygon points="{poly_points}" fill="none" stroke="#0f172a" stroke-width="3"/>
  {north}
  {"".join(labels)}
</svg>
"""
        return svg
