from __future__ import annotations

import json
import math
import re
from typing import Any, Optional

from shapely.geometry import Polygon
from sqlalchemy.orm import Session

from app.models.confrontante import Confrontante
from app.models.geometria import Geometria
from app.models.imovel import Imovel
from app.services.geometria_service import GeometriaService


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

    TERMOS_INSTITUCIONAIS_INVALIDOS = {
        "CARTORIO",
        "CARTÓRIO",
        "REGISTRO DE IMOVEIS",
        "REGISTRO DE IMÓVEIS",
        "OFICIO",
        "OFÍCIO",
        "COMARCA",
        "LIVRO",
        "FOLHA",
        "MATRICULA",
        "MATRÍCULA",
    }

    @staticmethod
    def _normalizar_texto(valor: Any) -> Optional[str]:
        if valor is None:
            return None

        texto = str(valor).strip()
        if not texto:
            return None

        texto = " ".join(texto.split())

        # limpeza leve para OCR real
        texto = (
            texto.replace(" ,", ",")
            .replace(" .", ".")
            .replace(" ;", ";")
            .replace(" :", ":")
        )

        return texto or None

    @staticmethod
    def _normalizar_texto_upper_sem_acentos(valor: Any) -> Optional[str]:
        texto = ConfrontanteService._normalizar_texto(valor)
        if not texto:
            return None

        return (
            texto.upper()
            .replace("-", " ")
            .replace("_", " ")
            .replace("Ç", "C")
            .replace("Ã", "A")
            .replace("Á", "A")
            .replace("À", "A")
            .replace("Â", "A")
            .replace("Ä", "A")
            .replace("É", "E")
            .replace("È", "E")
            .replace("Ê", "E")
            .replace("Ë", "E")
            .replace("Í", "I")
            .replace("Ì", "I")
            .replace("Î", "I")
            .replace("Ï", "I")
            .replace("Ó", "O")
            .replace("Ò", "O")
            .replace("Ô", "O")
            .replace("Õ", "O")
            .replace("Ö", "O")
            .replace("Ú", "U")
            .replace("Ù", "U")
            .replace("Û", "U")
            .replace("Ü", "U")
        )

    @staticmethod
    def _somente_digitos(valor: Any) -> str:
        return re.sub(r"\D", "", str(valor or ""))

    @staticmethod
    def _normalizar_matricula(valor: Any) -> Optional[str]:
        texto = ConfrontanteService._normalizar_texto(valor)
        if not texto:
            return None

        texto = re.sub(r"(?i)\bmatr[íi]cula\b[:\s\-#]*", "", texto)
        texto = re.sub(r"(?i)\bn[ºo°]?\b[:\s\-]*", "", texto)
        texto = texto.strip()
        texto = re.sub(r"[^\d./\-]", "", texto)

        return texto or None

    @staticmethod
    def _is_texto_institucional(valor: Any) -> bool:
        texto = ConfrontanteService._normalizar_texto_upper_sem_acentos(valor)
        if not texto:
            return False

        return any(
            termo in texto
            for termo in ConfrontanteService.TERMOS_INSTITUCIONAIS_INVALIDOS
        )

    @staticmethod
    def _normalizar_nome_confrontante(valor: Any) -> Optional[str]:
        texto = ConfrontanteService._normalizar_texto(valor)
        if not texto:
            return None

        if ConfrontanteService._is_texto_institucional(texto):
            return None

        return texto.upper()

    @staticmethod
    def _normalizar_identificacao_imovel(valor: Any) -> Optional[str]:
        texto = ConfrontanteService._normalizar_texto(valor)
        if not texto:
            return None

        return texto

    @staticmethod
    def _normalizar_descricao_confrontante(valor: Any) -> Optional[str]:
        texto = ConfrontanteService._normalizar_texto(valor)
        if not texto:
            return None

        if ConfrontanteService._is_texto_institucional(texto):
            return None

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
    # PARSER ROBUSTO DE GEOJSON
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
                    if not features:
                        raise ValueError("FeatureCollection sem features.")
                    geojson = features[0]["geometry"]

                elif tipo == "Feature":
                    geojson = geojson.get("geometry")

            return GeometriaService.parse_polygon_or_raise(geojson)

        except Exception as exc:
            raise ValueError("GeoJSON inválido para confrontantes.") from exc

    # =========================================================
    # DIREÇÃO DO SEGMENTO (GEOMÉTRICO)
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

        segmentos_base = GeometriaService.extract_segmentos(geometria.geojson)

        if not segmentos_base:
            return []

        try:
            geom = ConfrontanteService._parse_polygon_geojson(geometria.geojson)
            center = geom.centroid
            centerx = float(center.x)
            centery = float(center.y)
        except Exception:
            centerx = 0.0
            centery = 0.0

        segmentos: list[dict[str, Any]] = []

        for seg in segmentos_base:

            try:
                x1 = float(seg["ponto_inicial"]["x"])
                y1 = float(seg["ponto_inicial"]["y"])
                x2 = float(seg["ponto_final"]["x"])
                y2 = float(seg["ponto_final"]["y"])
                indice = int(seg.get("indice"))
            except Exception:
                continue

            midx = (x1 + x2) / 2.0
            midy = (y1 + y2) / 2.0

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
                    "ordem_segmento": indice,
                    "lado_label": f"LADO_{indice:02d}",
                    "direcao_normalizada": direcao,
                    "p1": (x1, y1),
                    "p2": (x2, y2),
                    "midpoint": (midx, midy),
                    "comprimento": float(comprimento),
                }
            )

        # 🔥 garantir ordem consistente
        segmentos.sort(key=lambda s: s["ordem_segmento"])

        return segmentos

    @staticmethod
    def _normalizar_item_confrontante(item: dict[str, Any]) -> Optional[dict[str, Any]]:
        if not isinstance(item, dict):
            return None

        # =========================================================
        # DIREÇÃO
        # =========================================================
        direcao_original = (
            item.get("direcao")
            or item.get("lado")
        )

        direcao_normalizada = ConfrontanteService._normalizar_direcao(direcao_original)

        # =========================================================
        # CAMPOS BRUTOS
        # =========================================================
        nome_raw = item.get("nome")
        descricao_raw = item.get("descricao")

        matricula_raw = (
            item.get("matricula")
            or item.get("numero_matricula")
        )

        identificacao_raw = (
            item.get("identificacao")
            or item.get("identificacao_imovel")
            or item.get("imovel")
        )

        # =========================================================
        # NORMALIZAÇÃO FORTE
        # =========================================================
        nome = ConfrontanteService._normalizar_nome_confrontante(nome_raw)
        descricao = ConfrontanteService._normalizar_descricao_confrontante(descricao_raw)
        matricula = ConfrontanteService._normalizar_matricula(matricula_raw)
        identificacao = ConfrontanteService._normalizar_identificacao_imovel(identificacao_raw)

        # =========================================================
        # DADOS COMPLEMENTARES
        # =========================================================
        tipo = ConfrontanteService._normalizar_texto(item.get("tipo"))
        lote = ConfrontanteService._normalizar_texto(item.get("lote"))
        gleba = ConfrontanteService._normalizar_texto(item.get("gleba"))

        # =========================================================
        # VALIDAÇÃO SEMÂNTICA REAL
        # =========================================================
        if not any([nome, descricao, matricula, identificacao]):
            return None

        # =========================================================
        # PROTEÇÃO CONTRA LIXO OCR
        # =========================================================
        if nome and ConfrontanteService._is_texto_institucional(nome):
            nome = None

        if descricao and ConfrontanteService._is_texto_institucional(descricao):
            descricao = None

        # revalida após limpeza
        if not any([nome, descricao, matricula, identificacao]):
            return None

        # =========================================================
        # PADRONIZAÇÃO FINAL
        # =========================================================
        if nome:
            nome = nome.strip().upper()

        if descricao:
            descricao = descricao.strip()

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

        if not segmentos_disponiveis:
            return None

        # =========================================================
        # PRIORIDADE 1 — MATCH EXATO DE DIREÇÃO
        # =========================================================
        if direcao_normalizada:
            candidatos = []

            for seg in segmentos_disponiveis:
                try:
                    if (
                        seg.get("ordem_segmento") not in usados
                        and seg.get("direcao_normalizada") == direcao_normalizada
                    ):
                        candidatos.append(seg)
                except Exception:
                    continue

            if candidatos:
                # maior segmento = mais representativo
                candidatos.sort(
                    key=lambda s: s.get("comprimento") or 0,
                    reverse=True
                )
                return candidatos[0]

        # =========================================================
        # PRIORIDADE 2 — MATCH POR PROXIMIDADE (fallback inteligente)
        # =========================================================
        for seg in segmentos_disponiveis:
            try:
                if seg.get("ordem_segmento") not in usados:
                    return seg
            except Exception:
                continue

        return None

    @staticmethod
    def extrair_confrontantes_do_texto(texto: str) -> list[dict[str, Any]]:
        import re

        if not texto:
            return []

        texto = str(texto)
        texto_upper = texto.upper()

        # =========================================================
        # REGEX BASE (direções)
        # =========================================================
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

            # =====================================================
            # LIMPEZA BÁSICA
            # =====================================================
            descricao = " ".join(descricao.split())

            # remove múltiplos separadores
            descricao = re.sub(r"\s{2,}", " ", descricao)

            # =====================================================
            # EXTRAÇÃO DE MATRÍCULA (se existir)
            # =====================================================
            matricula_match = re.search(
                r"\b\d{1,6}[/\.-]?\d{0,4}\b",
                descricao
            )

            matricula = None

            if matricula_match:
                matricula = matricula_match.group(0)

            # =====================================================
            # REMOÇÃO DE TERMOS INSTITUCIONAIS
            # =====================================================
            termos_ruins = [
                "CARTORIO",
                "CARTÓRIO",
                "REGISTRO DE IMOVEIS",
                "REGISTRO DE IMÓVEIS",
                "OFICIO",
                "OFÍCIO",
                "COMARCA",
            ]

            descricao_limpa = descricao

            for termo in termos_ruins:
                descricao_limpa = descricao_limpa.replace(termo, "")

            descricao_limpa = descricao_limpa.strip(" -,:;")

            if not descricao_limpa and not matricula:
                continue

            confrontantes.append({
                "direcao": direcao,
                "descricao": descricao_limpa or descricao,
                "matricula": matricula,
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
                confrontantes_ocr = ConfrontanteService.extrair_confrontantes_do_texto(
                    texto_base
                )

        if not confrontantes_ocr:
            return []

        if not geometria or not geometria.geojson:
            return []

        segmentos = ConfrontanteService._extrair_segmentos_geometria(geometria)

        # =========================================================
        # NORMALIZAÇÃO + DEDUPLICAÇÃO DO LOTE OCR
        # =========================================================
        itens_normalizados: list[dict[str, Any]] = []
        chaves_lote: set[tuple[str, str, str, str, str]] = set()

        for item in confrontantes_ocr:
            normalizado = ConfrontanteService._normalizar_item_confrontante(item)
            if not normalizado:
                continue

            chave_lote = (
                str(normalizado.get("direcao") or "").strip().upper(),
                str(normalizado.get("direcao_normalizada") or "").strip().upper(),
                str(normalizado.get("nome_confrontante") or "").strip().upper(),
                str(normalizado.get("matricula_confrontante") or "").strip().upper(),
                str(normalizado.get("identificacao_imovel_confrontante") or "").strip().upper(),
            )

            if chave_lote in chaves_lote:
                continue

            chaves_lote.add(chave_lote)
            itens_normalizados.append(normalizado)

        if not itens_normalizados:
            return []

        usados: set[int] = set()
        persistidos: list[Confrontante] = []

        # =========================================================
        # BASE ATUAL DO BANCO PARA O IMÓVEL
        # =========================================================
        confrontantes_existentes = (
            db.query(Confrontante)
            .filter(Confrontante.imovel_id == imovel.id)
            .all()
        )

        def _safe_upper(valor: Any) -> str:
            if valor is None:
                return ""
            return str(valor).strip().upper()

        def _enriquecer_observacoes(item: dict[str, Any]) -> str:
            observacoes_partes = ["Atualizado automaticamente via OCR/geometria"]

            if item.get("tipo"):
                observacoes_partes.append(f"TIPO={item.get('tipo')}")
            if item.get("lote"):
                observacoes_partes.append(f"LOTE={item.get('lote')}")
            if item.get("gleba"):
                observacoes_partes.append(f"GLEBA={item.get('gleba')}")

            return " | ".join(observacoes_partes)

        def _merge_texto(atual: Optional[str], novo: Optional[str]) -> Optional[str]:
            atual_limpo = ConfrontanteService._normalizar_texto(atual)
            novo_limpo = ConfrontanteService._normalizar_texto(novo)

            if atual_limpo and novo_limpo:
                # mantém o mais informativo
                return novo_limpo if len(novo_limpo) > len(atual_limpo) else atual_limpo

            return novo_limpo or atual_limpo

        def _localizar_existente(
            item: dict[str, Any],
            ordem_segmento: Optional[int],
            direcao_normalizada: Optional[str],
            nome_confrontante: Optional[str],
        ) -> Optional[Confrontante]:
            # =====================================================
            # 1. match por ordem_segmento (fonte mais forte)
            # =====================================================
            if ordem_segmento is not None:
                for existente in confrontantes_existentes:
                    if (
                        existente.imovel_id == imovel.id
                        and existente.ordem_segmento == ordem_segmento
                    ):
                        return existente

            # =====================================================
            # 2. match por geometria + direção normalizada
            # =====================================================
            if direcao_normalizada:
                for existente in confrontantes_existentes:
                    if (
                        existente.imovel_id == imovel.id
                        and existente.geometria_id == geometria.id
                        and _safe_upper(existente.direcao_normalizada) == _safe_upper(direcao_normalizada)
                    ):
                        return existente

            # =====================================================
            # 3. match por matrícula confrontante
            # =====================================================
            if item.get("matricula_confrontante"):
                for existente in confrontantes_existentes:
                    if (
                        existente.imovel_id == imovel.id
                        and _safe_upper(existente.matricula_confrontante)
                        == _safe_upper(item.get("matricula_confrontante"))
                    ):
                        return existente

            # =====================================================
            # 4. match por nome + identificação
            # =====================================================
            if nome_confrontante or item.get("identificacao_imovel_confrontante"):
                for existente in confrontantes_existentes:
                    if (
                        existente.imovel_id == imovel.id
                        and _safe_upper(existente.nome_confrontante) == _safe_upper(nome_confrontante)
                        and _safe_upper(existente.identificacao_imovel_confrontante)
                        == _safe_upper(item.get("identificacao_imovel_confrontante"))
                    ):
                        return existente

            # =====================================================
            # 5. match por nome + descrição
            # =====================================================
            if nome_confrontante or item.get("descricao"):
                for existente in confrontantes_existentes:
                    if (
                        existente.imovel_id == imovel.id
                        and _safe_upper(existente.nome_confrontante) == _safe_upper(nome_confrontante)
                        and _safe_upper(existente.descricao) == _safe_upper(item.get("descricao"))
                    ):
                        return existente

            return None

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

            if not direcao_normalizada:
                direcao_normalizada = "N"

            nome_confrontante = item.get("nome_confrontante")
            if nome_confrontante:
                nome_confrontante = nome_confrontante.strip().upper()

            observacoes_texto = _enriquecer_observacoes(item)

            existente = _localizar_existente(
                item=item,
                ordem_segmento=ordem_segmento,
                direcao_normalizada=direcao_normalizada,
                nome_confrontante=nome_confrontante,
            )

            if existente:
                existente.geometria_id = geometria.id
                existente.direcao = item["direcao"]
                existente.direcao_normalizada = direcao_normalizada
                existente.ordem_segmento = ordem_segmento
                existente.lado_label = lado_label

                existente.nome_confrontante = _merge_texto(
                    existente.nome_confrontante,
                    nome_confrontante,
                )

                existente.matricula_confrontante = _merge_texto(
                    existente.matricula_confrontante,
                    item.get("matricula_confrontante"),
                )

                existente.identificacao_imovel_confrontante = _merge_texto(
                    existente.identificacao_imovel_confrontante,
                    item.get("identificacao_imovel_confrontante"),
                )

                existente.descricao = _merge_texto(
                    existente.descricao,
                    item.get("descricao"),
                )

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
            db.flush()

            confrontantes_existentes.append(novo)
            persistidos.append(novo)

        db.commit()

        for item in persistidos:
            db.refresh(item)

        # =========================================================
        # GARANTIA FINAL — remove duplicados no retorno
        # =========================================================
        retorno_unico: list[Confrontante] = []
        ids_vistos: set[int] = set()

        for item in persistidos:
            if item.id in ids_vistos:
                continue
            ids_vistos.add(item.id)
            retorno_unico.append(item)

        return retorno_unico