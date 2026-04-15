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

        # 🔥 limpeza leve para OCR real
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

    # =========================================================
    # 🔥 PARSER ROBUSTO DE GEOJSON
    # =========================================================
    @staticmethod
    def _parse_polygon_geojson(geojson: Any) -> Polygon:
        try:
            if isinstance(geojson, str):
                geojson = json.loads(geojson)

            if isinstance(geojson, dict):
                tipo = geojson.get("type")

                if tipo == "FeatureCollection":
                    features = geojson.get("features") or []
                    geojson = features[0]["geometry"]

                elif tipo == "Feature":
                    geojson = geojson.get("geometry")

            return GeometriaService.parse_polygon_or_raise(geojson)

        except Exception as exc:
            raise ValueError("GeoJSON inválido para confrontantes.") from exc

    # =========================================================
    # 🔥 DIREÇÃO DO SEGMENTO (GEOMÉTRICO)
    # =========================================================
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

    # 🔥 distância euclidiana
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

        if not geometria or not geometria.geojson:
            return []

        # =========================================================
        # 🔥 FONTE ÚNICA DE VERDADE → GeometriaService
        # =========================================================
        segmentos_base = GeometriaService.extract_segmentos(geometria.geojson)

        if not segmentos_base:
            return []

        # =========================================================
        # 🔥 CENTROIDE PARA DIREÇÃO
        # =========================================================
        try:
            geom = ConfrontanteService._parse_polygon_geojson(geometria.geojson)
            center = geom.centroid
            centerx = float(center.x)
            centery = float(center.y)
        except Exception:
            centerx = 0.0
            centery = 0.0

        segmentos: list[dict[str, Any]] = []

        # =========================================================
        # 🔥 ENRIQUECIMENTO DOS SEGMENTOS
        # =========================================================
        for seg in segmentos_base:

            try:
                x1 = float(seg["ponto_inicial"]["x"])
                y1 = float(seg["ponto_inicial"]["y"])
                x2 = float(seg["ponto_final"]["x"])
                y2 = float(seg["ponto_final"]["y"])
            except Exception:
                continue

            midx = (x1 + x2) / 2.0
            midy = (y1 + y2) / 2.0

            # =====================================================
            # DIREÇÃO GEOMÉTRICA
            # =====================================================
            direcao = ConfrontanteService._segmento_direcao(
                midx=midx,
                midy=midy,
                centerx=centerx,
                centery=centery,
            )

            comprimento = ConfrontanteService._distancia(
                (x1, y1),
                (x2, y2),
            )

            segmentos.append(
                {
                    "ordem_segmento": int(seg.get("indice")),
                    "lado_label": f"LADO_{int(seg.get('indice')):02d}",
                    "direcao_normalizada": direcao,
                    "p1": (x1, y1),
                    "p2": (x2, y2),
                    "midpoint": (midx, midy),
                    "comprimento": float(comprimento),
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

        # 🔥 NOVO — preservar dados enriquecidos
        tipo = ConfrontanteService._normalizar_texto(item.get("tipo"))
        lote = ConfrontanteService._normalizar_texto(item.get("lote"))
        gleba = ConfrontanteService._normalizar_texto(item.get("gleba"))

        # 🔥 validação mínima
        if not nome and not descricao and not matricula and not identificacao:
            return None

        # 🔥 NORMALIZAÇÃO FORTE (PADRÃO GLOBAL DO SISTEMA)
        if nome:
            nome = nome.strip().upper()

        if descricao:
            descricao = descricao.strip()

        # 🔥 GARANTIR DIREÇÃO
        if not direcao_normalizada:
            direcao_normalizada = None  # será resolvido depois via geometria

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

        # =========================================================
        # 🔥 PRIORIDADE 1 — MATCH EXATO DE DIREÇÃO
        # =========================================================
        if direcao_normalizada:
            candidatos = [
                seg for seg in segmentos_disponiveis
                if seg["ordem_segmento"] not in usados
                and seg["direcao_normalizada"] == direcao_normalizada
            ]

            if candidatos:
                # 🔥 escolhe o maior segmento (mais representativo)
                candidatos.sort(key=lambda s: s.get("comprimento", 0), reverse=True)
                return candidatos[0]

        # =========================================================
        # 🔥 PRIORIDADE 2 — PRIMEIRO DISPONÍVEL
        # =========================================================
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

            ordem_segmento = None
            lado_label = None
            direcao_normalizada = item.get("direcao_normalizada")

            if segmento:
                ordem_segmento = segmento["ordem_segmento"]
                lado_label = segmento["lado_label"]

                if not direcao_normalizada:
                    direcao_normalizada = segmento["direcao_normalizada"]

                usados.add(segmento["ordem_segmento"])

            # 🔥 fallback de segurança
            if not direcao_normalizada:
                direcao_normalizada = "N"

            if ordem_segmento is None and segmento:
                ordem_segmento = segmento["ordem_segmento"]

            # 🔥 normalização forte do nome
            nome_confrontante = item.get("nome_confrontante")
            if nome_confrontante:
                nome_confrontante = nome_confrontante.strip().upper()

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

            if not existente and (nome_confrontante or item.get("descricao")):
                existente = (
                    db.query(Confrontante)
                    .filter(
                        Confrontante.imovel_id == imovel.id,
                        Confrontante.nome_confrontante == nome_confrontante,
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
                existente.nome_confrontante = nome_confrontante
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
                nome_confrontante=nome_confrontante,
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