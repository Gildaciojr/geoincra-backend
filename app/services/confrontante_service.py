from __future__ import annotations

import json
import math
from typing import Any, Optional

from shapely.geometry import Polygon, shape
from sqlalchemy.orm import Session

from app.models.confrontante import Confrontante
from app.models.geometria import Geometria
from app.services.geometria_service import GeometriaService
from app.models.imovel import Imovel


class ConfrontanteService:
    DIRECOES_VALIDAS = {
        "N",
        "S",
        "E",
        "W",
        "NE",
        "NW",
        "SE",
        "SW",
    }

    @staticmethod
    def _normalizar_texto(valor: Any) -> Optional[str]:
        if valor is None:
            return None

        texto = str(valor).strip()
        if not texto:
            return None

        texto = " ".join(texto.split())

        # 🔥 NOVO — limpeza leve para OCR real
        texto = (
            texto.replace(" ,", ",")
            .replace(" .", ".")
            .replace(" ;", ";")
            .replace(" :", ":")
        )

        return texto

    @staticmethod
    def _normalizar_direcao(valor: Any) -> Optional[str]:
        texto = ConfrontanteService._normalizar_texto(valor)
        if not texto:
            return None

        texto_upper = (
            texto.upper()
            .replace("-", " ")
            .replace("_", " ")
            .replace("Ç", "C")
            .replace("Ã", "A")
            .replace("Á", "A")
            .replace("À", "A")
            .replace("Â", "A")
            .replace("É", "E")
            .replace("Ê", "E")
            .replace("Í", "I")
            .replace("Ó", "O")
            .replace("Ô", "O")
            .replace("Õ", "O")
            .replace("Ú", "U")
        )

        mapa = {
            "N": "N",
            "NORTE": "N",
            "S": "S",
            "SUL": "S",
            "L": "E",
            "LESTE": "E",
            "E": "E",
            "O": "W",
            "OESTE": "W",
            "W": "W",
            "NE": "NE",
            "NORDESTE": "NE",
            "NO": "NW",
            "NOROESTE": "NW",
            "NW": "NW",
            "SE": "SE",
            "SUDESTE": "SE",
            "SO": "SW",
            "SUDOESTE": "SW",
            "SW": "SW",
        }

        return mapa.get(
            texto_upper,
            texto_upper if texto_upper in ConfrontanteService.DIRECOES_VALIDAS else None
        )

    @staticmethod
    def _parse_polygon_geojson(geojson: str) -> Polygon:
        try:
            return GeometriaService.parse_polygon_or_raise(geojson)
        except Exception as exc:
            raise ValueError("GeoJSON inválido para confrontantes.") from exc


    @staticmethod
    def _segmento_direcao(
        midx: float,
        midy: float,
        centerx: float,
        centery: float,
    ) -> str:
        dx = midx - centerx
        dy = midy - centery

        abs_dx = abs(dx)
        abs_dy = abs(dy)

        tolerancia = 0.15

        if abs_dx == 0 and abs_dy == 0:
            return "N"

        if abs_dx > 0 and abs_dy > 0:
            rel = min(abs_dx, abs_dy) / max(abs_dx, abs_dy)
            if rel >= tolerancia:
                if dx >= 0 and dy >= 0:
                    return "NE"
                if dx < 0 and dy >= 0:
                    return "NW"
                if dx >= 0 and dy < 0:
                    return "SE"
                return "SW"

        if abs_dx >= abs_dy:
            return "E" if dx >= 0 else "W"

        return "N" if dy >= 0 else "S"

    # 🔥 NOVO — distância euclidiana para futuras heurísticas
    @staticmethod
    def _distancia(
        p1: tuple[float, float],
        p2: tuple[float, float],
    ) -> float:
        dx = float(p2[0]) - float(p1[0])
        dy = float(p2[1]) - float(p1[1])
        return math.sqrt((dx * dx) + (dy * dy))

    @staticmethod
    def _extrair_segmentos_geometria(geometria: Geometria) -> list[dict[str, Any]]:
        geom = ConfrontanteService._parse_polygon_geojson(geometria.geojson)

        coords = list(geom.exterior.coords)
        if coords[0] != coords[-1]:
            coords.append(coords[0])

        center = geom.centroid
        centerx = float(center.x)
        centery = float(center.y)

        segmentos: list[dict[str, Any]] = []

        for i in range(len(coords) - 1):
            x1, y1 = coords[i]
            x2, y2 = coords[i + 1]

            midx = (float(x1) + float(x2)) / 2.0
            midy = (float(y1) + float(y2)) / 2.0

            direcao = ConfrontanteService._segmento_direcao(
                midx=midx,
                midy=midy,
                centerx=centerx,
                centery=centery,
            )

            # 🔥 NOVO — comprimento do segmento disponível para debug e futuras regras
            comprimento = ConfrontanteService._distancia(
                (float(x1), float(y1)),
                (float(x2), float(y2)),
            )

            segmentos.append(
                {
                    "ordem_segmento": i + 1,
                    "lado_label": f"LADO_{i + 1:02d}",
                    "direcao_normalizada": direcao,
                    "p1": (float(x1), float(y1)),
                    "p2": (float(x2), float(y2)),
                    "midpoint": (midx, midy),
                    "comprimento": comprimento,
                }
            )

        return segmentos

    @staticmethod
    def _normalizar_item_confrontante(item: dict[str, Any]) -> Optional[dict[str, Any]]:
        if not isinstance(item, dict):
            return None

        direcao_original = (
            item.get("direcao")
            or item.get("lado")
        )

        direcao_normalizada = ConfrontanteService._normalizar_direcao(direcao_original)
        nome = ConfrontanteService._normalizar_texto(item.get("nome"))
        descricao = ConfrontanteService._normalizar_texto(item.get("descricao"))
        matricula = ConfrontanteService._normalizar_texto(
            item.get("matricula")
            or item.get("numero_matricula")
        )
        identificacao = ConfrontanteService._normalizar_texto(
            item.get("identificacao")
            or item.get("identificacao_imovel")
            or item.get("imovel")
        )

        # 🔥 NOVO — preservar dados enriquecidos pelo normalizer sem quebrar contrato atual
        tipo = ConfrontanteService._normalizar_texto(item.get("tipo"))
        lote = ConfrontanteService._normalizar_texto(item.get("lote"))
        gleba = ConfrontanteService._normalizar_texto(item.get("gleba"))

        if not nome and not descricao and not matricula and not identificacao:
            return None

        return {
            "direcao": ConfrontanteService._normalizar_texto(direcao_original) or "NAO_INFORMADO",
            "direcao_normalizada": direcao_normalizada,
            "nome_confrontante": nome,
            "descricao": descricao,
            "matricula_confrontante": matricula,
            "identificacao_imovel_confrontante": identificacao,
            "tipo": tipo,
            "lote": lote,
            "gleba": gleba,
        }

    @staticmethod
    def _selecionar_segmento(
        segmentos_disponiveis: list[dict[str, Any]],
        direcao_normalizada: Optional[str],
        usados: set[int],
    ) -> Optional[dict[str, Any]]:
        if direcao_normalizada:
            for seg in segmentos_disponiveis:
                if seg["ordem_segmento"] in usados:
                    continue
                if seg["direcao_normalizada"] == direcao_normalizada:
                    return seg

        for seg in segmentos_disponiveis:
            if seg["ordem_segmento"] not in usados:
                return seg

        return None

    @staticmethod
    def extrair_confrontantes_do_texto(texto: str) -> list[dict[str, Any]]:
        import re

        if not texto:
            return []

        texto_upper = texto.upper()

        # 🔥 NOVO — regex um pouco mais tolerante
        padrao = re.findall(
            r"(NORTE|SUL|LESTE|OESTE|NORDESTE|NOROESTE|SUDESTE|SUDOESTE)\s*[:\-]\s*(.*?)(?=(NORTE|SUL|LESTE|OESTE|NORDESTE|NOROESTE|SUDESTE|SUDOESTE|$))",
            texto_upper,
            re.DOTALL,
        )

        confrontantes = []

        for direcao, conteudo, _ in padrao:
            descricao = conteudo.strip()

            if not descricao:
                continue

            confrontantes.append({
                "direcao": direcao,
                "descricao": descricao,
            })

        return confrontantes

    @staticmethod
    def processar_confrontantes(
        db: Session,
        imovel: Imovel,
        geometria: Geometria,
        confrontantes_ocr: list[dict[str, Any]] | None,
    ) -> list[Confrontante]:
        if not confrontantes_ocr:
            # 🔥 fallback inteligente via texto do imóvel
            texto_base = None

            try:
                texto_base = getattr(imovel, "descricao", None)
            except Exception:
                texto_base = None

            if texto_base:
                confrontantes_ocr = ConfrontanteService.extrair_confrontantes_do_texto(texto_base)

        if not confrontantes_ocr:
            return []

        if not geometria or not geometria.geojson:
            return []

        segmentos = ConfrontanteService._extrair_segmentos_geometria(geometria)

        itens_normalizados: list[dict[str, Any]] = []
        for item in confrontantes_ocr:
            normalizado = ConfrontanteService._normalizar_item_confrontante(item)
            if normalizado:
                itens_normalizados.append(normalizado)

        if not itens_normalizados:
            return []

        usados: set[int] = set()
        persistidos: list[Confrontante] = []

        for item in itens_normalizados:
            segmento = ConfrontanteService._selecionar_segmento(
                segmentos_disponiveis=segmentos,
                direcao_normalizada=item.get("direcao_normalizada"),
                usados=usados,
            )

            ordem_segmento = segmento["ordem_segmento"] if segmento else None
            lado_label = segmento["lado_label"] if segmento else None
            direcao_normalizada = (
                segmento["direcao_normalizada"]
                if segmento and not item.get("direcao_normalizada")
                else item.get("direcao_normalizada")
            )

            if segmento:
                usados.add(segmento["ordem_segmento"])

            existente = None

            if ordem_segmento is not None:
                existente = (
                    db.query(Confrontante)
                    .filter(
                        Confrontante.imovel_id == imovel.id,
                        Confrontante.ordem_segmento == ordem_segmento,
                    )
                    .first()
                )

            if not existente and direcao_normalizada:
                existente = (
                    db.query(Confrontante)
                    .filter(
                        Confrontante.imovel_id == imovel.id,
                        Confrontante.geometria_id == geometria.id,
                        Confrontante.direcao_normalizada == direcao_normalizada,
                    )
                    .first()
                )

            # 🔥 NOVO — fallback adicional por nome + descrição no mesmo imóvel
            if not existente and (item.get("nome_confrontante") or item.get("descricao")):
                existente = (
                    db.query(Confrontante)
                    .filter(
                        Confrontante.imovel_id == imovel.id,
                        Confrontante.nome_confrontante == item.get("nome_confrontante"),
                        Confrontante.descricao == item.get("descricao"),
                    )
                    .first()
                )

            observacoes_partes = ["Atualizado automaticamente via OCR/geometria"]

            if item.get("tipo"):
                observacoes_partes.append(f"TIPO={item.get('tipo')}")
            if item.get("lote"):
                observacoes_partes.append(f"LOTE={item.get('lote')}")
            if item.get("gleba"):
                observacoes_partes.append(f"GLEBA={item.get('gleba')}")

            observacoes_texto = " | ".join(observacoes_partes)

            if existente:
                existente.geometria_id = geometria.id
                existente.direcao = item["direcao"]
                existente.direcao_normalizada = direcao_normalizada
                existente.ordem_segmento = ordem_segmento
                existente.lado_label = lado_label
                existente.nome_confrontante = item.get("nome_confrontante")
                existente.matricula_confrontante = item.get("matricula_confrontante")
                existente.identificacao_imovel_confrontante = item.get("identificacao_imovel_confrontante")
                existente.descricao = item.get("descricao")
                existente.observacoes = observacoes_texto
                persistidos.append(existente)
                continue

            novo = Confrontante(
                imovel_id=imovel.id,
                geometria_id=geometria.id,
                direcao=item["direcao"],
                direcao_normalizada=direcao_normalizada,
                ordem_segmento=ordem_segmento,
                lado_label=lado_label,
                nome_confrontante=item.get("nome_confrontante"),
                matricula_confrontante=item.get("matricula_confrontante"),
                identificacao_imovel_confrontante=item.get("identificacao_imovel_confrontante"),
                descricao=item.get("descricao"),
                observacoes=observacoes_texto,
            )

            db.add(novo)
            persistidos.append(novo)

        db.commit()

        for item in persistidos:
            db.refresh(item)

        return persistidos