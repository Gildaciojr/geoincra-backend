from __future__ import annotations

import os
import math
from datetime import datetime
from typing import Any, List, Tuple

from pyproj import CRS, Transformer
from shapely.geometry import Polygon
from app.services.geometria_service import GeometriaService


class TxtLispService:

    PRECISAO = 6  # padrão técnico coordenadas
    PRECISAO_DIST = 3  # metros
    PRECISAO_ANG = 2  # segundos

    # =========================================================
    # NORMALIZAÇÃO
    # =========================================================
    @staticmethod
    def _format_float(value: float) -> str:
        return f"{value:.{TxtLispService.PRECISAO}f}"

    @staticmethod
    def _format_dist(value: float) -> str:
        return f"{value:.{TxtLispService.PRECISAO_DIST}f}"

    @staticmethod
    def _format_dist_lisp(value: float) -> str:
        return f"{value:.2f}"

    # =========================================================
    # AZIMUTE → DMS
    # =========================================================
    @staticmethod
    def _deg_to_dms(az: float) -> Tuple[int, int, float]:
        d = int(az)
        m_float = (az - d) * 60
        m = int(m_float)
        s = (m_float - m) * 60
        return d, m, s

    @staticmethod
    def _format_dms(az: float) -> str:
        d, m, s = TxtLispService._deg_to_dms(az)
        return f"{d:02d}°{m:02d}'{s:0{2 + TxtLispService.PRECISAO_ANG + 1}.{TxtLispService.PRECISAO_ANG}f}\""

    @staticmethod
    def _format_dms_inteiro(az: float) -> str:
        d, m, s = TxtLispService._deg_to_dms(az)

        segundos = int(round(s))
        minutos = m
        graus = d

        if segundos >= 60:
            segundos = 0
            minutos += 1

        if minutos >= 60:
            minutos = 0
            graus += 1

        if graus >= 360:
            graus -= 360

        return f"{graus:02d}°{minutos:02d}'{segundos:02d}\""
    
    @staticmethod
    def _format_azimute_decimal(az: float) -> str:
        d, m, s = TxtLispService._deg_to_dms(az)

        segundos = int(round(s))
        minutos = m
        graus = d

        if segundos >= 60:
            segundos = 0
            minutos += 1

        if minutos >= 60:
            minutos = 0
            graus += 1

        if graus >= 360:
            graus -= 360

        return (
             f"{graus}."
             f"{minutos:02d}"
             f"{segundos:02d}"
        )

    @staticmethod
    def _normalizar_nome_poligono(nome: Any, fallback: str = "IMOVEL") -> str:
        texto = " ".join(str(nome or "").strip().split())
        if not texto:
            texto = fallback

        texto = texto.replace("\n", " ").replace("\r", " ")
        texto = texto.strip(" ,;:-")

        if not texto:
            texto = fallback

        if texto[:1].isdigit():
            texto = f"POLIGONO {texto}"

        return texto

    @staticmethod
    def _coords_metricas(
        geojson: Any,
        epsg_origem: int | None = 4326,
    ) -> list[tuple[float, float]]:
        geom: Polygon = GeometriaService._parse_polygon_geojson(geojson)

        coords: list[tuple[float, float]] = [
            (float(x), float(y))
            for x, y in list(geom.exterior.coords)
        ]

        if len(coords) < 4:
            raise ValueError("Polígono inválido")

        if coords[0] != coords[-1]:
            coords.append(coords[0])

        try:
            epsg_int = int(epsg_origem or 0)
        except Exception:
            epsg_int = 0

        try:
            analise = GeometriaService.analisar_referencial(
                geojson=geojson,
                epsg_origem=epsg_int or 4326,
            )
        except Exception:
            analise = {}

        if (
            epsg_int > 0
            and analise.get("tipo_referencial") == "GEOGRAFICA"
        ):
            lon = float((analise.get("centroid") or {}).get("x") or coords[0][0])
            lat = float((analise.get("centroid") or {}).get("y") or coords[0][1])
            epsg_utm = GeometriaService._utm_epsg_from_lonlat(lon, lat)
            transformer = Transformer.from_crs(
                CRS.from_epsg(epsg_int),
                CRS.from_epsg(epsg_utm),
                always_xy=True,
            )

            coords_utm: list[tuple[float, float]] = []
            for x, y in coords:
                X, Y = transformer.transform(float(x), float(y))
                coords_utm.append((float(X), float(Y)))
            return coords_utm

        return coords

    # =========================================================
    # AZIMUTE E DISTÂNCIA
    # =========================================================
    @staticmethod
    def _calc_azimute(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]

        ang = math.degrees(math.atan2(dx, dy))
        if ang < 0:
            ang += 360.0

        return ang

    @staticmethod
    def _calc_distancia(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        return math.sqrt(dx * dx + dy * dy)

    # =========================================================
    # TXT ORIGINAL (MANTIDO)
    # =========================================================
    @staticmethod
    def gerar_txt(geojson: str) -> str:
        try:
            geom: Polygon = GeometriaService._parse_polygon_geojson(geojson)
        except Exception as exc:
            raise ValueError("Geometria inválida para exportação TXT") from exc

        coords: List[Tuple[float, float]] = list(geom.exterior.coords)

        if len(coords) < 4:
            raise ValueError("Polígono inválido para TXT")

        if coords[0] != coords[-1]:
            coords.append(coords[0])

        linhas: List[str] = []

        linhas.append("############################################")
        linhas.append("# ARQUIVO DE COORDENADAS - GEOINCRA")
        linhas.append(f"# GERADO EM: {datetime.utcnow().isoformat()}")
        linhas.append(f"# TOTAL VERTICES: {len(coords) - 1}")
        linhas.append("# FORMATO: VERTICE, X, Y")
        linhas.append("############################################")
        linhas.append("")

        for i, (x, y) in enumerate(coords[:-1], start=1):
            linhas.append(
                f"V{i},"
                f"{TxtLispService._format_float(float(x))},"
                f"{TxtLispService._format_float(float(y))}"
            )

        linhas.append("")
        linhas.append("# FECHAMENTO")

        x0, y0 = coords[0]
        linhas.append(
            f"V{len(coords)},"
            f"{TxtLispService._format_float(float(x0))},"
            f"{TxtLispService._format_float(float(y0))}"
        )

        return "\n".join(linhas)

    # =========================================================
    # 🔥 NOVO — PERÍMETRO TÉCNICO (ENGENHARIA)
    # =========================================================
    @staticmethod
    def gerar_txt_perimetro(
        geojson: str,
        nome_poligono: str | None = None,
        numero_matricula: str | None = None,
        descricao_imovel: str | None = None,
        epsg_origem: int | None = 4326,
    ) -> str:
        try:
            coords = TxtLispService._coords_metricas(
                geojson=geojson,
                epsg_origem=epsg_origem,
            )
        except Exception as exc:
            raise ValueError("Geometria inválida para perímetro") from exc

        linhas: List[str] = []

        # =========================================================
        # HEADER
        # =========================================================
        linhas.append("RESUMO DOS PERÍMETROS DOS IMÓVEIS")
        linhas.append("Individual por Matrícula")
        linhas.append("")
        linhas.append(
            "Descrição Completa do Imóvel: "
            f"{descricao_imovel or nome_poligono or 'NÃO INFORMADO'}"
        )

        if numero_matricula:
            linhas.append(f"Matrícula: {numero_matricula}")

        linhas.append("Descrição Técnica:")
        linhas.append(f"# GERADO EM: {datetime.utcnow().isoformat()}")
        linhas.append(f"# TOTAL SEGMENTOS: {len(coords) - 1}")
        linhas.append("# FORMATO: @distancia<azimute")

        perimetro_total = 0.0

        # =========================================================
        # SEGMENTOS
        # =========================================================
        for i in range(len(coords) - 1):
            p1 = coords[i]
            p2 = coords[i + 1]

            distancia = TxtLispService._calc_distancia(p1, p2)
            azimute = TxtLispService._calc_azimute(p1, p2)

            perimetro_total += distancia

            linha = (
                f"@{TxtLispService._format_dist_lisp(distancia)}"
                f"<{TxtLispService._format_dms_inteiro(azimute)}"
            )

            linhas.append(linha)

    # =========================================================
    # RESUMO FINAL
    # =========================================================
        linhas.append(
            f"Perímetro Total: "
            f"{TxtLispService._format_dist_lisp(perimetro_total)} m"
        )

        return "\n".join(linhas)

    # =========================================================
    # 🔥 TXT LISP / CAD (PADRÃO CLIENTE)
    # =========================================================
    @staticmethod
    def gerar_txt_lisp(
        geojson: str | None = None,
        nome_poligono: str | None = None,
        poligonos: list[dict[str, Any]] | None = None,
        epsg_origem: int | None = 4326,
    ) -> str:
        itens: list[dict[str, Any]] = []

        if poligonos:
            itens = [
                item
                for item in poligonos
                if isinstance(item, dict)
            ]
        elif geojson is not None:
            itens = [
                {
                    "geojson": geojson,
                    "nome_poligono": nome_poligono,
                    "epsg_origem": epsg_origem,
                }
            ]

        if not itens:
            raise ValueError("Nenhum polígono informado para TXT LISP")

        linhas: List[str] = []

        for item in itens:
            item_geojson = item.get("geojson")
            item_nome = TxtLispService._normalizar_nome_poligono(
                item.get("nome_poligono")
                or item.get("nome")
                or nome_poligono
            )

            item_epsg = item.get("epsg_origem", epsg_origem)

            try:
                coords = TxtLispService._coords_metricas(
                    geojson=item_geojson,
                    epsg_origem=item_epsg,
                )

            except Exception as exc:
                raise ValueError(
                    "Geometria inválida para TXT LISP"
                ) from exc

            if len(coords) < 4:
                raise ValueError(
                    "Polígono inválido para TXT LISP"
                )

            # =====================================================
            # NOME DO POLÍGONO
            # =====================================================

            linhas.append(item_nome)

            # =====================================================
            # SEGMENTOS
            # =====================================================

            total_segmentos = 0

            for i in range(len(coords) - 1):

                p1 = coords[i]
                p2 = coords[i + 1]

                distancia = (
                    TxtLispService._calc_distancia(
                        p1,
                        p2,
                    )
                )

                azimute = (
                    TxtLispService._calc_azimute(
                        p1,
                        p2,
                    )
                )

                azimute_fmt = (
                    TxtLispService._format_azimute_decimal(
                        azimute
                    )
                )

                distancia_fmt = (
                    TxtLispService._format_dist_lisp(
                        distancia
                    )
                )

                linhas.append(
                    f"{azimute_fmt},{distancia_fmt}"
                )

                total_segmentos += 1

            if total_segmentos < 3:
                raise ValueError(
                    "Polígono inválido para TXT LISP: mínimo de 3 lados"
                )

        return "\n".join(linhas)

    # =========================================================
    # SALVAR TXT
    # =========================================================
    @staticmethod
    def salvar_txt(
        imovel_id: int,
        txt: str,
        base_dir: str = "app/uploads/imoveis",
    ) -> str:

        ts = int(datetime.utcnow().timestamp())

        folder = os.path.join(
            base_dir,
            str(imovel_id),
            "cad",
        )

        os.makedirs(folder, exist_ok=True)

        filename = (
            f"vertices_profissional_{ts}.txt"
        )

        path = os.path.join(folder, filename)

        with open(
            path,
            "w",
            encoding="utf-8",
        ) as f:
            f.write(txt)

        return path

    # =========================================================
    # SALVAR TXT PERÍMETRO
    # =========================================================
    @staticmethod
    def salvar_txt_perimetro(
        imovel_id: int,
        txt: str,
        base_dir: str = "app/uploads/imoveis",
    ) -> str:

        ts = int(datetime.utcnow().timestamp())

        folder = os.path.join(
            base_dir,
            str(imovel_id),
            "cad",
        )

        os.makedirs(folder, exist_ok=True)

        filename = (
            f"perimetro_tecnico_{ts}.txt"
        )

        path = os.path.join(folder, filename)

        with open(
            path,
            "w",
            encoding="utf-8",
        ) as f:
            f.write(txt)

        return path

    # =========================================================
    # SALVAR TXT LISP / CAD
    # =========================================================
    @staticmethod
    def salvar_txt_lisp(
        imovel_id: int,
        txt: str,
        base_dir: str = "app/uploads/imoveis",
    ) -> str:

        ts = int(datetime.utcnow().timestamp())

        folder = os.path.join(
            base_dir,
            str(imovel_id),
            "cad",
        )

        os.makedirs(folder, exist_ok=True)

        filename = (
            f"lisp_cad_{ts}.txt"
        )

        path = os.path.join(folder, filename)

        with open(
            path,
            "w",
            encoding="utf-8",
        ) as f:
            f.write(txt)

        return path
