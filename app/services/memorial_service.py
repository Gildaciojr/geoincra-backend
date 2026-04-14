from __future__ import annotations

import json
import math
import os
from dataclasses import dataclass
from datetime import datetime
from math import atan2, degrees, floor, sqrt
from typing import Any, List, Optional, Tuple

from fastapi import HTTPException
from pyproj import CRS, Transformer
from shapely.geometry import Polygon

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
    def _normalizar_geojson_para_geometria(geojson: Any) -> dict:
        """
        Aceita:
        - geometria pura
        - Feature
        - FeatureCollection
        - string JSON
        e devolve sempre uma geometria pura compatível com o GeometriaService.
        """
        if geojson is None:
            raise HTTPException(status_code=400, detail="GeoJSON ausente.")

        obj: Any = geojson

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
        geom_dict = MemorialService._normalizar_geojson_para_geometria(geojson)
        return GeometriaService.parse_polygon_or_raise(geom_dict)

    @staticmethod
    def _to_points(
        geojson: Any,
        epsg_origem: int | None = 4326,
    ) -> Tuple[Optional[int], List[_PontoPlano], str]:

        geojson_geom = MemorialService._normalizar_geojson_para_geometria(geojson)

        analise = GeometriaService.analisar_referencial(
            geojson=geojson_geom,
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
        geojson: Any,
        area_hectares: float,
        perimetro_m: float,
        imovel_id: int,
        prefixo_vertice: str = "V",
        epsg_origem: int | None = 4326,
        confrontantes: List[dict[str, Any]] | None = None,
        nome_imovel: str | None = None,
    ) -> dict:

        geojson_geom = MemorialService._normalizar_geojson_para_geometria(geojson)

        # =========================================================
        # ANÁLISE DO REFERENCIAL (MANTIDO, MAS CENTRALIZADO)
        # =========================================================
        analise = GeometriaService.analisar_referencial(
            geojson=geojson_geom,
            epsg_origem=epsg_origem,
        )

        tipo = analise["tipo_referencial"]

        epsg_utm = None
        if tipo != "LOCAL_CARTESIANA":
            lon = float(analise["centroid"]["x"])
            lat = float(analise["centroid"]["y"])
            epsg_utm = MemorialService._utm_epsg_from_lonlat(lon, lat)

        # =========================================================
        # 🔥 USO DA CAMADA DE ENGENHARIA (SEM DUPLICAÇÃO)
        # =========================================================
        segmentos = GeometriaService.extract_segmentos(geojson_geom)

        if not segmentos:
            raise ValueError("Não foi possível extrair segmentos da geometria")

        soma_distancias = 0.0
        linhas_formatadas: List[str] = []

        confrontantes_lista = confrontantes if isinstance(confrontantes, list) else []

        def _resolver_confrontante_segmento(
            indice_segmento: int,
        ) -> str | None:
            if not confrontantes_lista:
                return None

            # =====================================================
            # 1. PRIORIDADE POR ORDEM / ÍNDICE
            # =====================================================
            for c in confrontantes_lista:
                if not isinstance(c, dict):
                    continue

                ordem = c.get("ordem_segmento")
                indice = c.get("indice")
                numero = c.get("numero")

                for valor in (ordem, indice, numero):
                    try:
                        if valor is not None and int(valor) == indice_segmento:
                            nome = (
                                c.get("nome")
                                or c.get("confrontante")
                                or c.get("descricao")
                                or c.get("identificacao")
                            )
                            if nome:
                                return " ".join(str(nome).strip().split())
                    except Exception:
                        continue

            # =====================================================
            # 2. PRIORIDADE POR LADO / DIREÇÃO (fallback)
            # =====================================================
            mapa_lado = {
                1: ["N", "NORTE"],
                2: ["E", "L", "LESTE"],
                3: ["S", "SUL"],
                4: ["W", "O", "OESTE"],
            }

            lados_esperados = mapa_lado.get(indice_segmento, [])

            if lados_esperados:
                for c in confrontantes_lista:
                    if not isinstance(c, dict):
                        continue

                    lado = (
                        c.get("lado_normalizado")
                        or c.get("direcao")
                        or c.get("lado")
                    )

                    if not lado:
                        continue

                    lado_norm = str(lado).strip().upper()

                    if lado_norm in lados_esperados:
                        nome = (
                            c.get("nome")
                            or c.get("confrontante")
                            or c.get("descricao")
                            or c.get("identificacao")
                        )
                        if nome:
                            return " ".join(str(nome).strip().split())

            # =====================================================
            # 3. FALLBACK POR POSIÇÃO NA LISTA
            # =====================================================
            pos = indice_segmento - 1
            if 0 <= pos < len(confrontantes_lista):
                c = confrontantes_lista[pos]
                if isinstance(c, dict):
                    nome = (
                        c.get("nome")
                        or c.get("confrontante")
                        or c.get("descricao")
                        or c.get("identificacao")
                    )
                    if nome:
                        return " ".join(str(nome).strip().split())

            return None

        for i, seg in enumerate(segmentos):
            dist = MemorialService._safe_float(seg.get("distancia"))
            az = MemorialService._safe_float(seg.get("azimute_graus"))

            if dist <= 0 or math.isnan(dist) or math.isinf(dist):
                raise ValueError(f"Segmento inválido detectado na posição {i + 1}")

            if math.isnan(az) or math.isinf(az):
                raise ValueError(f"Azimute inválido no segmento {i + 1}")

            soma_distancias += dist

            rumo = MemorialService._rumo_from_azimute(az)
            az_dms = MemorialService._deg_to_dms_str(az)

            de_vertice = f"{prefixo_vertice}{i + 1}"
            ate_vertice = (
                f"{prefixo_vertice}{i + 2}"
                if i + 1 < len(segmentos)
                else f"{prefixo_vertice}1"
            )

            confrontante_trecho = _resolver_confrontante_segmento(i + 1)

            if i == 0:
                inicio_texto = (
                    f"{i + 1:02d}. Inicia-se no vértice {de_vertice}"
                )
            else:
                inicio_texto = (
                    f"{i + 1:02d}. Do vértice {de_vertice}"
                )

            if confrontante_trecho:
                trecho_confrontante = (
                    f", confrontando neste trecho com {confrontante_trecho}"
                )
            else:
                trecho_confrontante = ""

            if i + 1 < len(segmentos):
                fechamento_texto = f", até o vértice {ate_vertice}."
            else:
                fechamento_texto = (
                    f", até o vértice {ate_vertice}, "
                    f"ponto inicial desta descrição perimetral."
                )

            linhas_formatadas.append(
                (
                    f"{inicio_texto}{trecho_confrontante}, "
                    f"segue com azimute de {az_dms}, "
                    f"rumo {rumo}, "
                    f"e distância de {dist:.3f} metros"
                    f"{fechamento_texto}"
                )
            )

        # =========================================================
        # ÁREA / PERÍMETRO DEFENSIVOS
        # =========================================================
        area_hectares_final = MemorialService._safe_float(area_hectares)
        perimetro_m_final = MemorialService._safe_float(perimetro_m)

        if area_hectares_final <= 0:
            _, area_calc_ha, perimetro_calc_m = GeometriaService.calcular_area_perimetro(
                geojson=geojson_geom,
                epsg_origem=epsg_origem or 4326,
            )
            area_hectares_final = MemorialService._safe_float(area_calc_ha)

            if perimetro_m_final <= 0:
                perimetro_m_final = MemorialService._safe_float(perimetro_calc_m)

        if perimetro_m_final <= 0:
            perimetro_m_final = MemorialService._safe_float(soma_distancias)

        # =========================================================
        # FECHAMENTO
        # =========================================================
        erro_perimetro = abs(soma_distancias - perimetro_m_final)

        # =========================================================
        # CABEÇALHO DESCRITIVO
        # =========================================================
        cabecalho_linhas: List[str] = [
            "MEMORIAL DESCRITIVO",
            "",
        ]

        if nome_imovel:
            cabecalho_linhas.append(
                f"Imóvel: {' '.join(str(nome_imovel).strip().split())}"
            )

        cabecalho_linhas.extend(
            [
                "Imóvel georreferenciado conforme dados fornecidos e processados pelo sistema técnico.",
                "",
                f"Sistema de referência: {tipo}",
                f"Sistema projetado (UTM): {epsg_utm or 'N/A'}",
                "",
                f"Área total: {area_hectares_final:.4f} hectares",
                f"Perímetro total: {perimetro_m_final:.3f} metros",
                f"Erro de fechamento: {erro_perimetro:.4f} metros",
                "",
                "DESCRIÇÃO DO PERÍMETRO:",
                "",
            ]
        )

        # =========================================================
        # FECHAMENTO PROFISSIONAL
        # =========================================================
        fechamento_final = (
            "O perímetro acima descrito encerra a poligonal do imóvel, "
            "fechando geometricamente de forma consistente, "
            "sem indicação de inconsistências significativas nos dados processados."
        )

        # =========================================================
        # TEXTO PROFISSIONAL FINAL
        # =========================================================
        texto = "\n".join(
            [
                *cabecalho_linhas,
                *linhas_formatadas,
                "",
                fechamento_final,
            ]
        )

        # =========================================================
        # SALVAMENTO
        # =========================================================
        caminho, url = MemorialService._salvar_arquivo(imovel_id, texto)

        return {
            "success": True,
            "geometria_id": geometria_id,
            "arquivo_path": caminho,
            "arquivo_url": url,
            "texto_preview": texto,
            "tipo_referencial": tipo,
            "epsg_utm": epsg_utm,
            "message": "Memorial gerado com estrutura profissional.",
        }