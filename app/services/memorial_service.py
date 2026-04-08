from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from datetime import datetime
from math import atan2, degrees, floor, sqrt
from typing import List, Optional, Tuple

from fastapi import HTTPException
from pyproj import CRS, Transformer
from shapely.geometry import Polygon, shape

from app.services.geometria_service import GeometriaService


@dataclass(frozen=True)
class _PontoPlano:
    x: float
    y: float


class MemorialService:

    BASE_UPLOAD_DIR = "app/uploads/imoveis"

    @staticmethod
    def _safe_float(value):
        try:
            v = float(value)
            if math.isnan(v) or math.isinf(v):
                return 0.0
            return v
        except Exception:
            return 0.0

    @staticmethod
    def _utm_epsg_from_lonlat(lon: float, lat: float) -> int:
        zona = int(floor((lon + 180.0) / 6.0) + 1)
        return 32600 + zona if lat >= 0 else 32700 + zona

    @staticmethod
    def _parse_polygon(geojson: str) -> Polygon:
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
            raise HTTPException(status_code=400, detail="Geometria inválida.")

        return geom

    @staticmethod
    def _to_points(
        geojson: str,
        epsg_origem: int | None = 4326,
    ) -> Tuple[Optional[int], List[_PontoPlano], str]:

        analise = GeometriaService.analisar_referencial(
            geojson=geojson,
            epsg_origem=epsg_origem,
        )

        geom: Polygon = analise["geom"]
        tipo_referencial = str(analise["tipo_referencial"])

        coords = list(geom.exterior.coords)

        coords = [
            (
                MemorialService._safe_float(x),
                MemorialService._safe_float(y),
            )
            for x, y in coords
        ]

        if len(coords) < 4:
            raise HTTPException(status_code=400, detail="Polígono inválido.")

        if coords[0] != coords[-1]:
            coords.append(coords[0])

        if len(coords) < 4:
            raise HTTPException(status_code=400, detail="Polígono inválido após normalização.")

        if tipo_referencial == "LOCAL_CARTESIANA":
            return (
                None,
                [_PontoPlano(float(x), float(y)) for x, y in coords],
                tipo_referencial,
            )

        lon = float(analise["centroid"]["x"])
        lat = float(analise["centroid"]["y"])
        epsg_utm = MemorialService._utm_epsg_from_lonlat(lon, lat)

        transformer = Transformer.from_crs(
            CRS.from_epsg(epsg_origem),
            CRS.from_epsg(epsg_utm),
            always_xy=True,
        )

        pontos: List[_PontoPlano] = []

        for x, y in coords:
            X, Y = transformer.transform(float(x), float(y))

            X = MemorialService._safe_float(X)
            Y = MemorialService._safe_float(Y)

            pontos.append(_PontoPlano(X, Y))

        if len(pontos) < 4:
            raise HTTPException(status_code=400, detail="Geometria insuficiente após projeção.")

        return epsg_utm, pontos, tipo_referencial

    @staticmethod
    def _dist_m(p1, p2):
        return sqrt((p2.x - p1.x) ** 2 + (p2.y - p1.y) ** 2)

    @staticmethod
    def _azimute_deg(p1, p2):
        dx = p2.x - p1.x
        dy = p2.y - p1.y
        ang = degrees(atan2(dx, dy))
        return ang + 360 if ang < 0 else ang

    @staticmethod
    def _deg_to_dms_str(deg: float) -> str:
        d = int(deg)
        m = int((deg - d) * 60)
        s = ((deg - d) * 60 - m) * 60
        return f"{d:02d}°{m:02d}'{s:05.2f}\""

    @staticmethod
    def _rumo_from_azimute(az: float) -> str:
        az = az % 360
        if az < 90:
            return f"N {MemorialService._deg_to_dms_str(az)} E"
        if az < 180:
            return f"S {MemorialService._deg_to_dms_str(180 - az)} E"
        if az < 270:
            return f"S {MemorialService._deg_to_dms_str(az - 180)} W"
        return f"N {MemorialService._deg_to_dms_str(360 - az)} W"

    @staticmethod
    def _salvar_arquivo(imovel_id: int, texto: str) -> tuple[str, str]:

        pasta = f"{MemorialService.BASE_UPLOAD_DIR}/{imovel_id}/memorial"
        os.makedirs(pasta, exist_ok=True)

        timestamp = int(datetime.utcnow().timestamp())
        nome_arquivo = f"memorial_{timestamp}.txt"

        caminho = f"{pasta}/{nome_arquivo}"

        with open(caminho, "w", encoding="utf-8") as f:
            f.write(texto)

        base_url = "https://geoincra.escriturafacil.com"
        url = f"{base_url}/{caminho.replace('app/', '')}"

        return caminho, url

    @staticmethod
    def gerar_memorial(
        geometria_id: int,
        geojson: str,
        area_hectares: float,
        perimetro_m: float,
        imovel_id: int,
        prefixo_vertice: str = "V",
        epsg_origem: int | None = 4326,
    ) -> dict:

        epsg_utm, pts, tipo = MemorialService._to_points(geojson, epsg_origem)

        if len(pts) < 4:
            raise ValueError("Geometria insuficiente para gerar memorial")

        linhas = []
        soma_distancias = 0.0

        for i in range(len(pts) - 1):
            p1, p2 = pts[i], pts[i + 1]

            dist = MemorialService._dist_m(p1, p2)
            az = MemorialService._azimute_deg(p1, p2)

            if dist <= 0 or math.isnan(dist) or math.isinf(dist):
                raise ValueError(f"Segmento inválido detectado na posição {i+1}")

            if math.isnan(az) or math.isinf(az):
                raise ValueError(f"Azimute inválido no segmento {i+1}")

            soma_distancias += dist

            linhas.append(
                {
                    "ordem": i + 1,
                    "de_vertice": f"{prefixo_vertice}{i + 1}",
                    "ate_vertice": f"{prefixo_vertice}{i + 2}" if i + 1 < len(pts) - 1 else f"{prefixo_vertice}1",
                    "azimute_graus": az,
                    "rumo": MemorialService._rumo_from_azimute(az),
                    "distancia_m": dist,
                }
            )

        erro_perimetro = abs(soma_distancias - (perimetro_m or soma_distancias))

        texto = "\n".join([
            "MEMORIAL DESCRITIVO",
            "",
            f"Referencial: {tipo}",
            f"EPSG UTM: {epsg_utm or 'N/A'}",
            f"Área (ha): {area_hectares:.4f}",
            f"Perímetro (m): {perimetro_m:.3f}",
            f"Erro de fechamento (m): {erro_perimetro:.4f}",
            "",
            "DESCRIÇÃO DOS SEGMENTOS:",
            "",
            *[
                f"{l['ordem']:02d}. {l['de_vertice']} -> {l['ate_vertice']} | "
                f"Azimute: {l['azimute_graus']:.6f}° | "
                f"Rumo: {l['rumo']} | "
                f"Distância: {l['distancia_m']:.3f} m"
                for l in linhas
            ]
        ])

        caminho, url = MemorialService._salvar_arquivo(imovel_id, texto)

        return {
            "success": True,
            "geometria_id": geometria_id,
            "arquivo_path": caminho,
            "arquivo_url": url,
            "texto_preview": texto,
            "tipo_referencial": tipo,
            "epsg_utm": epsg_utm,
            "message": "Memorial gerado com arquivo físico.",
        }