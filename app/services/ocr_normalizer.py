from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


# =========================================================
# HELPERS
# =========================================================
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


def _normalizar_direcao(valor: Any) -> Optional[str]:
    """
    Normaliza direções de confrontantes para padrão técnico.

    Entrada:
        "norte", "N", "n", "NOROESTE", "so", etc

    Saída:
        "N", "S", "E", "W", "NE", "NW", "SE", "SW"
    """
    texto = _normalizar_texto(valor)
    if not texto:
        return None

    texto = (
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

    return mapa.get(texto, texto if texto in mapa.values() else None)


# =========================================================
# VALIDAÇÕES CRÍTICAS
# =========================================================
def _validar_segmentos(segmentos: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not segmentos:
        raise ValueError("Nenhum segmento informado pelo OCR")

    validados: List[Dict[str, Any]] = []

    for i, s in enumerate(segmentos, start=1):
        az = s.get("azimute_raw")
        dist = s.get("distancia")

        if not az:
            raise ValueError(f"Segmento {i} inválido: azimute ausente")

        if dist is None:
            raise ValueError(f"Segmento {i} inválido: distância ausente")

        if not isinstance(dist, (int, float)) or dist <= 0:
            raise ValueError(f"Segmento {i} inválido: distância inválida")

        validados.append({
            "azimute_raw": az,
            "distancia": float(dist),
        })

    if len(validados) < 3:
        raise ValueError("Segmentos insuficientes para formar polígono")

    return validados


# =========================================================
# NORMALIZADOR PRINCIPAL (ENDURECIDO)
# =========================================================
def normalizar_dados_ocr(dados: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(dados, dict):
        raise ValueError("OCR retornou estrutura inválida (não é dict)")

    resultado: Dict[str, Any] = {}
    erros: List[str] = []
    warnings: List[str] = []

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

    if not resultado["matricula"]["numero"]:
        warnings.append("Matrícula não identificada")

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
        else:
            warnings.append("Unidade de área desconhecida")

    resultado["imovel"] = {
        "descricao": _normalizar_texto(dados.get("descricao_imovel")),
        "area": {
            "valor": area,
            "unidade_original": unidade,
            "hectares": hectares,
        },
    }

    if area is None:
        warnings.append("Área não identificada")

    # =========================================================
    # PROPRIETÁRIOS
    # =========================================================
    proprietarios_raw = dados.get("proprietarios") or []
    proprietarios: List[Dict[str, Optional[str]]] = []

    for i, p in enumerate(proprietarios_raw, start=1):
        if not isinstance(p, dict):
            continue

        nome = _normalizar_texto(p.get("nome"))
        cpf_cnpj = _normalizar_cpf_cnpj(p.get("cpf_cnpj"))

        if not nome:
            warnings.append(f"Proprietário {i} ignorado (sem nome)")
            continue

        proprietarios.append({
            "nome": nome,
            "cpf_cnpj": cpf_cnpj,
        })

    if not proprietarios:
        warnings.append("Nenhum proprietário válido identificado")

    resultado["proprietarios"] = proprietarios

    # =========================================================
    # SEGMENTOS (CRÍTICO)
    # =========================================================
    segmentos_raw = dados.get("segmentos_memorial") or []
    segmentos: List[Dict[str, Any]] = []

    for s in segmentos_raw:
        if not isinstance(s, dict):
            continue

        azimute_raw = s.get("azimute") or s.get("rumo")
        distancia = _to_float(s.get("distancia"))

        segmentos.append({
            "azimute_raw": _normalizar_texto(azimute_raw),
            "distancia": distancia,
        })

    segmentos_validos: List[Dict[str, Any]] = []

    try:
        segmentos_validos = _validar_segmentos(segmentos)
    except Exception as exc:
        erros.append(str(exc))

    # =========================================================
    # GEOMETRIA
    # =========================================================
    geojson = dados.get("geojson") or dados.get("geometria")
    memorial_texto = _normalizar_texto(dados.get("memorial_texto"))

    fonte: Optional[str] = None

    if segmentos_validos:
        fonte = "segmentos"
    elif memorial_texto:
        fonte = "memorial"
    elif geojson:
        fonte = "geojson"

    resultado["geometria"] = {
        "fonte": fonte,
        "geojson": geojson,
        "segmentos": segmentos_validos,
        "memorial_texto": memorial_texto,
    }

    # =========================================================
    # CONFRONTANTES
    # =========================================================
    confrontantes_raw = dados.get("confrontantes") or []
    confrontantes: List[Dict[str, Optional[str]]] = []

    for i, c in enumerate(confrontantes_raw, start=1):
        if not isinstance(c, dict):
            warnings.append(f"Confrontante {i} ignorado (estrutura inválida)")
            continue

        nome = _normalizar_texto(c.get("nome"))
        descricao = _normalizar_texto(c.get("descricao"))
        lado_original = _normalizar_texto(c.get("direcao") or c.get("lado"))
        lado_normalizado = _normalizar_direcao(c.get("direcao") or c.get("lado"))
        matricula_confrontante = _normalizar_texto(
            c.get("matricula")
            or c.get("numero_matricula")
        )
        identificacao = _normalizar_texto(
            c.get("identificacao")
            or c.get("identificacao_imovel")
            or c.get("imovel")
        )

        if not nome and not descricao and not matricula_confrontante and not identificacao:
            warnings.append(f"Confrontante {i} ignorado (sem conteúdo útil)")
            continue

        confrontantes.append(
            {
                "lado": lado_original,
                "lado_normalizado": lado_normalizado,
                "nome": nome,
                "descricao": descricao,
                "matricula": matricula_confrontante,
                "identificacao": identificacao,
            }
        )

    resultado["confrontantes"] = confrontantes

    # =========================================================
    # SCORE DE QUALIDADE (REAL)
    # =========================================================
    score = 100

    if not segmentos_validos:
        score -= 40

    if not resultado["matricula"]["numero"]:
        score -= 10

    if not proprietarios:
        score -= 10

    if area is None:
        score -= 10

    if geojson is None and not segmentos_validos:
        score -= 30

    score = max(score, 0)

    resultado["qualidade"] = {
        "score": score,
        "erros": erros,
        "warnings": warnings,
    }

    # =========================================================
    # FAIL HARD (CRÍTICO)
    # =========================================================
    if erros:
        raise ValueError(f"OCR inválido: {erros}")

    return resultado