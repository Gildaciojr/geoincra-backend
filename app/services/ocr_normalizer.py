from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


def _to_float(valor: Any) -> Optional[float]:
    if isinstance(valor, (int, float)):
        return float(valor)

    if not isinstance(valor, str):
        return None

    texto = valor.strip().replace(".", "").replace(",", ".")
    try:
        return float(texto)
    except Exception:
        return None


def _normalizar_texto(valor: Any) -> Optional[str]:
    if not isinstance(valor, str):
        return None

    texto = " ".join(valor.strip().split())
    return texto or None


def _normalizar_cpf_cnpj(valor: Any) -> Optional[str]:
    if not isinstance(valor, str):
        return None

    numeros = re.sub(r"\D", "", valor)

    if len(numeros) == 11:
        return f"{numeros[:3]}.{numeros[3:6]}.{numeros[6:9]}-{numeros[9:]}"
    if len(numeros) == 14:
        return f"{numeros[:2]}.{numeros[2:5]}.{numeros[5:8]}/{numeros[8:12]}-{numeros[12:]}"
    return valor.strip()


def normalizar_dados_ocr(dados: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(dados, dict):
        return {}

    resultado: Dict[str, Any] = {}

    # =========================================================
    # MATRÍCULA
    # =========================================================
    numero_matricula = (
        dados.get("numero_matricula")
        or dados.get("matricula")
    )

    resultado["matricula"] = {
        "numero": _normalizar_texto(numero_matricula),
        "comarca": _normalizar_texto(dados.get("comarca")),
        "cartorio": _normalizar_texto(dados.get("cartorio")),
    }

    # =========================================================
    # IMÓVEL
    # =========================================================
    area_raw = dados.get("area_total")
    unidade_raw = dados.get("unidade_area")

    area = _to_float(area_raw)
    unidade = _normalizar_texto(unidade_raw)

    hectares: Optional[float] = None

    if area is not None:
        if unidade and unidade.lower() in ["ha", "hectare", "hectares"]:
            hectares = area
        elif unidade and unidade.lower() in ["m2", "m²"]:
            hectares = area / 10000.0

    resultado["imovel"] = {
        "descricao": _normalizar_texto(dados.get("descricao_imovel")),
        "area": {
            "valor": area,
            "unidade_original": unidade,
            "hectares": hectares,
        },
    }

    # =========================================================
    # PROPRIETÁRIOS
    # =========================================================
    proprietarios_raw = dados.get("proprietarios") or []
    proprietarios: List[Dict[str, Optional[str]]] = []

    for p in proprietarios_raw:
        if not isinstance(p, dict):
            continue

        nome = _normalizar_texto(p.get("nome"))
        cpf_cnpj = _normalizar_cpf_cnpj(p.get("cpf_cnpj"))

        if not nome:
            continue

        proprietarios.append({
            "nome": nome,
            "cpf_cnpj": cpf_cnpj,
        })

    resultado["proprietarios"] = proprietarios

    # =========================================================
    # SEGMENTOS
    # =========================================================
    segmentos_raw = dados.get("segmentos_memorial") or []
    segmentos: List[Dict[str, Any]] = []

    for s in segmentos_raw:
        if not isinstance(s, dict):
            continue

        azimute_raw = s.get("azimute") or s.get("rumo")
        distancia = _to_float(s.get("distancia"))

        if azimute_raw is None or distancia is None:
            continue

        segmentos.append({
            "azimute_raw": _normalizar_texto(azimute_raw),
            "distancia": distancia,
        })

    # =========================================================
    # GEOMETRIA
    # =========================================================
    geojson = dados.get("geojson") or dados.get("geometria")
    memorial_texto = _normalizar_texto(dados.get("memorial_texto"))

    fonte: Optional[str] = None

    if geojson:
        fonte = "geojson"
    elif len(segmentos) >= 3:
        fonte = "segmentos"
    elif memorial_texto:
        fonte = "memorial"

    resultado["geometria"] = {
        "fonte": fonte,
        "geojson": geojson,
        "segmentos": segmentos,
        "memorial_texto": memorial_texto,
    }

    # =========================================================
    # CONFRONTANTES
    # =========================================================
    confrontantes_raw = dados.get("confrontantes") or []
    confrontantes: List[Dict[str, Optional[str]]] = []

    for c in confrontantes_raw:
        if not isinstance(c, dict):
            continue

        lado = _normalizar_texto(c.get("direcao") or c.get("lado"))
        nome = _normalizar_texto(c.get("nome"))
        descricao = _normalizar_texto(c.get("descricao"))

        if not nome:
            continue

        confrontantes.append({
            "lado": lado,
            "nome": nome,
            "descricao": descricao,
        })

    resultado["confrontantes"] = confrontantes

    # =========================================================
    # QUALIDADE (INTELIGENTE)
    # =========================================================
    resultado["qualidade"] = {
        "tem_geojson": geojson is not None,
        "tem_segmentos": len(segmentos) >= 3,
        "tem_memorial": bool(memorial_texto),
        "tem_area": area is not None,
        "tem_proprietarios": len(proprietarios) > 0,
    }

    return resultado