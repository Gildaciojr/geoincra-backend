from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


# =========================================================
# HELPERS BÁSICOS
# =========================================================
def _is_blank(valor: Any) -> bool:
    if valor is None:
        return True
    if isinstance(valor, str) and not valor.strip():
        return True
    return False


def _normalizar_espacos(texto: str) -> str:
    return " ".join(texto.strip().split())


def _normalizar_texto(valor: Any) -> Optional[str]:
    if valor is None:
        return None

    if isinstance(valor, bool):
        return None

    if isinstance(valor, (int, float)):
        valor = str(valor)

    if not isinstance(valor, str):
        return None

    texto = _normalizar_espacos(valor)

    if not texto:
        return None

    return texto


def _normalizar_texto_upper_sem_acentos(valor: Any) -> Optional[str]:
    texto = _normalizar_texto(valor)
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


def _coalesce(*valores: Any) -> Any:
    for valor in valores:
        if isinstance(valor, str):
            if valor.strip():
                return valor
        elif valor is not None:
            return valor
    return None


def _first_dict(*valores: Any) -> Optional[Dict[str, Any]]:
    for valor in valores:
        if isinstance(valor, dict):
            return valor
    return None


def _first_list(*valores: Any) -> Optional[List[Any]]:
    for valor in valores:
        if isinstance(valor, list):
            return valor
    return None


def _somente_digitos(valor: Any) -> str:
    return re.sub(r"\D", "", str(valor or ""))


def _to_float(valor: Any) -> Optional[float]:
    if valor is None:
        return None

    if isinstance(valor, bool):
        return None

    if isinstance(valor, (int, float)):
        return float(valor)

    if not isinstance(valor, str):
        return None

    texto = valor.strip()
    if not texto:
        return None

    texto = texto.replace("R$", "").replace(" ", "")

    # casos:
    # 1.234,56 -> 1234.56
    # 1234,56 -> 1234.56
    # 1,234.56 -> 1234.56
    # 1234.56 -> 1234.56
    if "," in texto and "." in texto:
        if texto.rfind(",") > texto.rfind("."):
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")
    else:
        if "," in texto:
            texto = texto.replace(".", "").replace(",", ".")
        else:
            texto = texto.replace(",", "")

    try:
        return float(texto)
    except Exception:
        return None


def _normalizar_matricula(valor: Any) -> Optional[str]:
    texto = _normalizar_texto(valor)
    if not texto:
        return None

    texto = re.sub(r"(?i)\bmatr[íi]cula\b[:\s\-#]*", "", texto)
    texto = re.sub(r"(?i)\bn[ºo°]\b[:\s\-]*", "", texto)
    texto = texto.strip()
    texto = re.sub(r"[^\d./\-]", "", texto)

    if not texto:
        return None

    return texto


def _normalizar_cpf_cnpj(valor: Any) -> Optional[str]:
    if valor is None:
        return None

    numeros = _somente_digitos(valor)

    if len(numeros) == 11:
        return f"{numeros[:3]}.{numeros[3:6]}.{numeros[6:9]}-{numeros[9:]}"
    if len(numeros) == 14:
        return f"{numeros[:2]}.{numeros[2:5]}.{numeros[5:8]}/{numeros[8:12]}-{numeros[12:]}"

    texto = _normalizar_texto(valor)
    return texto


def _normalizar_tipo_proprietario(valor: Any) -> Optional[str]:
    texto_upper = _normalizar_texto_upper_sem_acentos(valor)
    if not texto_upper:
        return None

    mapa = {
        "PROPRIETARIO": "PROPRIETARIO",
        "PROPRIETARIA": "PROPRIETARIO",
        "PROPRIETARIOS": "PROPRIETARIO",
        "HERDEIRO": "HERDEIRO",
        "HERDEIRA": "HERDEIRO",
        "HERDEIROS": "HERDEIRO",
        "ESPOLIO": "ESPOLIO",
        "INVENTARIANTE": "INVENTARIANTE",
        "COPROPRIETARIO": "COPROPRIETARIO",
        "COPROPRIETARIA": "COPROPRIETARIO",
        "CESSIONARIO": "CESSIONARIO",
        "CESSIONARIA": "CESSIONARIO",
        "PROMITENTE COMPRADOR": "PROMITENTE_COMPRADOR",
        "PROMITENTE VENDEDOR": "PROMITENTE_VENDEDOR",
        "NU PROPRIETARIO": "NU_PROPRIETARIO",
        "USUFRUTUARIO": "USUFRUTUARIO",
    }

    return mapa.get(texto_upper, texto_upper.replace(" ", "_"))


def _normalizar_unidade_area(valor: Any) -> Optional[str]:
    texto = _normalizar_texto_upper_sem_acentos(valor)
    if not texto:
        return None

    mapa = {
        "HA": "ha",
        "HECTARE": "ha",
        "HECTARES": "ha",
        "M2": "m2",
        "M²": "m2",
        "METRO QUADRADO": "m2",
        "METROS QUADRADOS": "m2",
        "KM2": "km2",
        "KM²": "km2",
        "QUILOMETRO QUADRADO": "km2",
        "QUILOMETROS QUADRADOS": "km2",
        "ALQUEIRE": "alqueire",
        "ALQUEIRES": "alqueire",
    }

    return mapa.get(texto, texto.lower())


def _converter_area_para_hectares(area: Optional[float], unidade: Optional[str]) -> Optional[float]:
    if area is None:
        return None

    if not unidade:
        return None

    unidade = unidade.lower()

    if unidade == "ha":
        return area
    if unidade == "m2":
        return area / 10000.0
    if unidade == "km2":
        return area * 100.0

    # não converter alqueire automaticamente sem contexto regional
    return None


def _normalizar_direcao(valor: Any) -> Optional[str]:
    texto = _normalizar_texto_upper_sem_acentos(valor)
    if not texto:
        return None

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


def _normalizar_lado_original(valor: Any) -> Optional[str]:
    texto_upper = _normalizar_texto_upper_sem_acentos(valor)
    if not texto_upper:
        return None

    mapa = {
        "N": "NORTE",
        "NORTE": "NORTE",
        "S": "SUL",
        "SUL": "SUL",
        "L": "LESTE",
        "LESTE": "LESTE",
        "E": "LESTE",
        "O": "OESTE",
        "OESTE": "OESTE",
        "W": "OESTE",
        "NE": "NORDESTE",
        "NORDESTE": "NORDESTE",
        "NO": "NOROESTE",
        "NOROESTE": "NOROESTE",
        "NW": "NOROESTE",
        "SE": "SUDESTE",
        "SUDESTE": "SUDESTE",
        "SO": "SUDOESTE",
        "SUDOESTE": "SUDOESTE",
        "SW": "SUDOESTE",
    }

    return mapa.get(texto_upper, texto_upper)


def _normalizar_geojson(valor: Any) -> Optional[Dict[str, Any]]:
    if valor is None:
        return None

    if isinstance(valor, dict):
        return valor

    if isinstance(valor, str):
        texto = valor.strip()
        if not texto:
            return None

        # propositalmente sem json.loads para não endurecer demais aqui
        # o pipeline já revalida quando for resolver geojson
        return None

    return None


def _normalizar_memorial_texto(valor: Any) -> Optional[str]:
    texto = _normalizar_texto(valor)
    if not texto:
        return None
    return texto


def _normalizar_numero_vertice(valor: Any) -> Optional[str]:
    texto = _normalizar_texto(valor)
    if not texto:
        return None
    return texto.upper()


def _normalizar_identificacao_generica(valor: Any) -> Optional[str]:
    texto = _normalizar_texto(valor)
    if not texto:
        return None
    return texto


def _extrair_lote_gleba_de_texto(valor: Any) -> Dict[str, Optional[str]]:
    texto = _normalizar_texto(valor)
    if not texto:
        return {
            "lote": None,
            "gleba": None,
        }

    lote = None
    gleba = None

    match_lote = re.search(r"(?i)\blote\s+([a-z0-9.\-\/]+)", texto)
    if match_lote:
        lote = match_lote.group(1).strip()

    match_gleba = re.search(r"(?i)\bgleba\s+([a-z0-9.\-\/]+)", texto)
    if match_gleba:
        gleba = match_gleba.group(1).strip()

    return {
        "lote": lote,
        "gleba": gleba,
    }


def _inferir_tipo_confrontante(nome: Optional[str], descricao: Optional[str], identificacao: Optional[str]) -> Optional[str]:
    base = " ".join(
        part for part in [nome, descricao, identificacao] if part
    ).lower()

    if not base:
        return None

    if "estrada" in base or "rodovia" in base or "vicinal" in base:
        return "estrada"
    if "rio" in base or "córrego" in base or "corrego" in base or "ribeirão" in base or "ribeirao" in base:
        return "curso_dagua"
    if "área pública" in base or "area publica" in base or "patrimônio público" in base or "patrimonio publico" in base:
        return "area_publica"
    if "reserva legal" in base:
        return "reserva_legal"
    if "lote" in base or "gleba" in base or "fazenda" in base or "sítio" in base or "sitio" in base:
        return "imovel_rural"

    return "outro"


def _deduplicar_proprietarios(
    proprietarios: List[Dict[str, Optional[str]]]
) -> List[Dict[str, Optional[str]]]:
    vistos: set[tuple[str, str, str]] = set()
    resultado: List[Dict[str, Optional[str]]] = []

    for item in proprietarios:
        nome = item.get("nome") or ""
        cpf_cnpj = item.get("cpf_cnpj") or ""
        tipo = item.get("tipo") or ""

        chave = (
            nome.upper(),
            _somente_digitos(cpf_cnpj),
            tipo.upper(),
        )

        if chave in vistos:
            continue

        vistos.add(chave)
        resultado.append(item)

    return resultado


def _deduplicar_confrontantes(
    confrontantes: List[Dict[str, Optional[str]]]
) -> List[Dict[str, Optional[str]]]:
    vistos: set[tuple[str, str, str, str, str]] = set()
    resultado: List[Dict[str, Optional[str]]] = []

    for item in confrontantes:
        lado = item.get("lado") or ""
        nome = item.get("nome") or ""
        matricula = item.get("matricula") or ""
        identificacao = item.get("identificacao") or ""
        descricao = item.get("descricao") or ""

        chave = (
            lado.upper(),
            nome.upper(),
            matricula.upper(),
            identificacao.upper(),
            descricao.upper(),
        )

        if chave in vistos:
            continue

        vistos.add(chave)
        resultado.append(item)

    return resultado


def _deduplicar_warnings(warnings: List[str]) -> List[str]:
    vistos: set[str] = set()
    resultado: List[str] = []

    for item in warnings:
        chave = item.strip().lower()
        if not chave or chave in vistos:
            continue
        vistos.add(chave)
        resultado.append(item)

    return resultado


# =========================================================
# EXTRAÇÃO FLEXÍVEL DE BLOCOS
# =========================================================
def _resolver_bloco_matricula(dados: Dict[str, Any]) -> Dict[str, Any]:
    matricula_dict = _first_dict(dados.get("matricula"))

    numero = _coalesce(
        dados.get("numero_matricula"),
        matricula_dict.get("numero") if matricula_dict else None,
        matricula_dict.get("numero_matricula") if matricula_dict else None,
        dados.get("matricula") if not isinstance(dados.get("matricula"), dict) else None,
    )

    comarca = _coalesce(
        dados.get("comarca"),
        matricula_dict.get("comarca") if matricula_dict else None,
    )

    cartorio = _coalesce(
        dados.get("cartorio"),
        dados.get("nome_cartorio"),
        matricula_dict.get("cartorio") if matricula_dict else None,
        matricula_dict.get("nome_cartorio") if matricula_dict else None,
    )

    livro = _coalesce(
        dados.get("livro"),
        matricula_dict.get("livro") if matricula_dict else None,
    )

    folha = _coalesce(
        dados.get("folha"),
        matricula_dict.get("folha") if matricula_dict else None,
    )

    codigo_cartorio = _coalesce(
        dados.get("codigo_cartorio"),
        dados.get("codigo_cartorio_id"),
        dados.get("codigo"),
        matricula_dict.get("codigo_cartorio") if matricula_dict else None,
        matricula_dict.get("codigo_cartorio_id") if matricula_dict else None,
    )

    return {
        "numero": _normalizar_matricula(numero),
        "comarca": _normalizar_texto(comarca),
        "cartorio": _normalizar_texto(cartorio),
        "livro": _normalizar_texto(livro),
        "folha": _normalizar_texto(folha),
        "codigo_cartorio": _normalizar_texto(codigo_cartorio),
    }


def _resolver_bloco_imovel(dados: Dict[str, Any], warnings: List[str]) -> Dict[str, Any]:
    imovel_dict = _first_dict(dados.get("imovel"))

    descricao = _coalesce(
        dados.get("descricao_imovel"),
        imovel_dict.get("descricao") if imovel_dict else None,
        imovel_dict.get("descricao_imovel") if imovel_dict else None,
    )

    area_raw = _coalesce(
        dados.get("area_total"),
        imovel_dict.get("area_total") if imovel_dict else None,
        imovel_dict.get("area") if imovel_dict else None,
        _first_dict(imovel_dict.get("area") if imovel_dict else None).get("valor")
        if isinstance(imovel_dict.get("area") if imovel_dict else None, dict)
        else None,
    )

    unidade_raw = _coalesce(
        dados.get("unidade_area"),
        imovel_dict.get("unidade_area") if imovel_dict else None,
        _first_dict(imovel_dict.get("area") if imovel_dict else None).get("unidade_original")
        if isinstance(imovel_dict.get("area") if imovel_dict else None, dict)
        else None,
    )

    area_valor = _to_float(area_raw)
    unidade = _normalizar_unidade_area(unidade_raw)
    hectares = _converter_area_para_hectares(area_valor, unidade)

    if area_valor is None:
        warnings.append("Área não identificada")

    if area_valor is not None and unidade is None:
        warnings.append("Unidade de área não identificada")
    elif area_valor is not None and hectares is None and unidade not in [None, "ha", "m2", "km2"]:
        warnings.append(f"Unidade de área sem conversão automática: {unidade}")

    return {
        "descricao": _normalizar_texto(descricao),
        "area": {
            "valor": area_valor,
            "unidade_original": unidade,
            "hectares": hectares,
        },
    }


def _resolver_proprietarios(dados: Dict[str, Any], warnings: List[str]) -> List[Dict[str, Optional[str]]]:
    proprietarios_raw = _first_list(
        dados.get("proprietarios"),
        dados.get("titulares"),
        dados.get("proprietario"),
    ) or []

    proprietarios: List[Dict[str, Optional[str]]] = []

    for i, p in enumerate(proprietarios_raw, start=1):
        if isinstance(p, str):
            nome = _normalizar_texto(p)
            if nome:
                proprietarios.append(
                    {
                        "nome": nome,
                        "cpf_cnpj": None,
                        "tipo": "PROPRIETARIO",
                    }
                )
            else:
                warnings.append(f"Proprietário {i} ignorado (string vazia)")
            continue

        if not isinstance(p, dict):
            warnings.append(f"Proprietário {i} ignorado (estrutura inválida)")
            continue

        nome = _normalizar_texto(
            _coalesce(
                p.get("nome"),
                p.get("razao_social"),
                p.get("titular"),
            )
        )
        cpf_cnpj = _normalizar_cpf_cnpj(
            _coalesce(
                p.get("cpf_cnpj"),
                p.get("cpf"),
                p.get("cnpj"),
                p.get("documento"),
            )
        )
        tipo = _normalizar_tipo_proprietario(
            _coalesce(
                p.get("tipo"),
                p.get("qualidade"),
                "PROPRIETARIO",
            )
        )

        if not nome:
            warnings.append(f"Proprietário {i} ignorado (sem nome)")
            continue

        proprietarios.append(
            {
                "nome": nome,
                "cpf_cnpj": cpf_cnpj,
                "tipo": tipo,
            }
        )

    proprietarios = _deduplicar_proprietarios(proprietarios)

    if not proprietarios:
        warnings.append("Nenhum proprietário válido identificado")

    return proprietarios


def _resolver_segmentos(dados: Dict[str, Any], warnings: List[str]) -> tuple[List[Dict[str, Any]], List[str]]:
    erros: List[str] = []
    segmentos_raw = _first_list(
        dados.get("segmentos_memorial"),
        dados.get("segmentos"),
        _first_dict(dados.get("geometria")).get("segmentos") if isinstance(dados.get("geometria"), dict) else None,
    ) or []

    segmentos: List[Dict[str, Any]] = []

    for i, s in enumerate(segmentos_raw, start=1):
        if not isinstance(s, dict):
            warnings.append(f"Segmento {i} ignorado (estrutura inválida)")
            continue

        azimute_raw = _normalizar_texto(
            _coalesce(
                s.get("azimute_raw"),
                s.get("azimute"),
                s.get("rumo"),
                s.get("bearing"),
            )
        )
        distancia = _to_float(
            _coalesce(
                s.get("distancia"),
                s.get("distancia_m"),
                s.get("comprimento"),
                s.get("length"),
            )
        )

        ordem = s.get("ordem")
        vertice_inicial = _normalizar_numero_vertice(
            _coalesce(
                s.get("vertice_inicial"),
                s.get("inicio"),
                s.get("ponto_inicial"),
                s.get("de"),
            )
        )
        vertice_final = _normalizar_numero_vertice(
            _coalesce(
                s.get("vertice_final"),
                s.get("fim"),
                s.get("ponto_final"),
                s.get("para"),
            )
        )

        if not azimute_raw and distancia is None:
            warnings.append(f"Segmento {i} ignorado (sem azimute/rumo e sem distância)")
            continue

        if not azimute_raw:
            erros.append(f"Segmento {i} inválido: azimute/rumo ausente")
            continue

        if distancia is None:
            erros.append(f"Segmento {i} inválido: distância ausente")
            continue

        if distancia <= 0:
            erros.append(f"Segmento {i} inválido: distância inválida")
            continue

        segmento: Dict[str, Any] = {
            "azimute_raw": azimute_raw,
            "distancia": float(distancia),
        }

        if ordem is not None:
            segmento["ordem"] = ordem
        if vertice_inicial:
            segmento["vertice_inicial"] = vertice_inicial
        if vertice_final:
            segmento["vertice_final"] = vertice_final

        segmentos.append(segmento)

    # regra segura:
    # - menos de 3 segmentos não é erro fatal se existir memorial_texto ou geojson;
    # - vira warning e o pipeline pode usar outra fonte geométrica.
    if segmentos and len(segmentos) < 3:
        warnings.append("Segmentos insuficientes para formar polígono; será tentado memorial_texto/geojson")
        segmentos = []

    return segmentos, erros


def _resolver_geometria(
    dados: Dict[str, Any],
    segmentos_validos: List[Dict[str, Any]],
    warnings: List[str],
) -> Dict[str, Any]:
    geometria_dict = _first_dict(dados.get("geometria"))
    geojson = _normalizar_geojson(
        _coalesce(
            dados.get("geojson"),
            geometria_dict.get("geojson") if geometria_dict else None,
            dados.get("geometria") if isinstance(dados.get("geometria"), dict) else None,
        )
    )

    memorial_texto = _normalizar_memorial_texto(
        _coalesce(
            dados.get("memorial_texto"),
            geometria_dict.get("memorial_texto") if geometria_dict else None,
            geometria_dict.get("texto") if geometria_dict else None,
        )
    )

    fonte: Optional[str] = None

    if segmentos_validos:
        fonte = "segmentos"
    elif memorial_texto:
        fonte = "memorial"
    elif geojson:
        fonte = "geojson"

    if not fonte:
        warnings.append("Nenhuma fonte geométrica válida identificada")

    return {
        "fonte": fonte,
        "geojson": geojson,
        "segmentos": segmentos_validos,
        "memorial_texto": memorial_texto,
    }


def _resolver_confrontantes(dados: Dict[str, Any], warnings: List[str]) -> List[Dict[str, Optional[str]]]:
    confrontantes_raw = _first_list(
        dados.get("confrontantes"),
        dados.get("limites"),
        dados.get("divisas"),
    ) or []

    confrontantes: List[Dict[str, Optional[str]]] = []

    for i, c in enumerate(confrontantes_raw, start=1):
        if isinstance(c, str):
            descricao = _normalizar_texto(c)
            if not descricao:
                warnings.append(f"Confrontante {i} ignorado (string vazia)")
                continue

            extraidos = _extrair_lote_gleba_de_texto(descricao)
            confrontantes.append(
                {
                    "lado": None,
                    "lado_normalizado": None,
                    "nome": None,
                    "descricao": descricao,
                    "matricula": None,
                    "identificacao": descricao,
                    "tipo": _inferir_tipo_confrontante(None, descricao, descricao),
                    "lote": extraidos["lote"],
                    "gleba": extraidos["gleba"],
                }
            )
            continue

        if not isinstance(c, dict):
            warnings.append(f"Confrontante {i} ignorado (estrutura inválida)")
            continue

        lado_bruto = _coalesce(
            c.get("direcao"),
            c.get("lado"),
            c.get("face"),
            c.get("posicao"),
        )

        nome = _normalizar_texto(
            _coalesce(
                c.get("nome"),
                c.get("confrontante"),
            )
        )

        descricao = _normalizar_texto(
            _coalesce(
                c.get("descricao"),
                c.get("descricao_completa"),
                c.get("texto"),
            )
        )

        matricula_confrontante = _normalizar_matricula(
            _coalesce(
                c.get("matricula"),
                c.get("numero_matricula"),
            )
        )

        identificacao = _normalizar_identificacao_generica(
            _coalesce(
                c.get("identificacao"),
                c.get("identificacao_imovel"),
                c.get("imovel"),
                c.get("nome_imovel"),
            )
        )

        lote = _normalizar_texto(
            _coalesce(
                c.get("lote"),
                _extrair_lote_gleba_de_texto(nome).get("lote") if nome else None,
                _extrair_lote_gleba_de_texto(descricao).get("lote") if descricao else None,
                _extrair_lote_gleba_de_texto(identificacao).get("lote") if identificacao else None,
            )
        )

        gleba = _normalizar_texto(
            _coalesce(
                c.get("gleba"),
                _extrair_lote_gleba_de_texto(nome).get("gleba") if nome else None,
                _extrair_lote_gleba_de_texto(descricao).get("gleba") if descricao else None,
                _extrair_lote_gleba_de_texto(identificacao).get("gleba") if identificacao else None,
            )
        )

        tipo = _normalizar_texto(
            _coalesce(
                c.get("tipo"),
                _inferir_tipo_confrontante(nome, descricao, identificacao),
            )
        )

        lado_original = _normalizar_lado_original(lado_bruto)
        lado_normalizado = _normalizar_direcao(lado_bruto)

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
                "tipo": tipo,
                "lote": lote,
                "gleba": gleba,
            }
        )

    confrontantes = _deduplicar_confrontantes(confrontantes)

    if not confrontantes:
        warnings.append("Nenhum confrontante válido identificado")

    return confrontantes


def _calcular_score_qualidade(
    matricula: Dict[str, Any],
    imovel: Dict[str, Any],
    proprietarios: List[Dict[str, Any]],
    geometria: Dict[str, Any],
    confrontantes: List[Dict[str, Any]],
) -> int:
    score = 100

    if not matricula.get("numero"):
        score -= 12

    if not matricula.get("comarca"):
        score -= 4

    if not imovel.get("descricao"):
        score -= 5

    area = imovel.get("area") or {}
    if area.get("valor") is None:
        score -= 10
    if area.get("hectares") is None and area.get("valor") is not None:
        score -= 4

    if not proprietarios:
        score -= 12

    segmentos = geometria.get("segmentos") or []
    memorial_texto = geometria.get("memorial_texto")
    geojson = geometria.get("geojson")

    if not segmentos and not memorial_texto and not geojson:
        score -= 35
    elif not segmentos:
        score -= 10

    if not confrontantes:
        score -= 8

    return max(score, 0)


# =========================================================
# NORMALIZADOR PRINCIPAL
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
    matricula = _resolver_bloco_matricula(dados)
    resultado["matricula"] = {
        "numero": matricula["numero"],
        "comarca": matricula["comarca"],
        "cartorio": matricula["cartorio"],
    }

    # campos legados/auxiliares para o restante do backend
    resultado["numero_matricula"] = matricula["numero"]
    resultado["comarca"] = matricula["comarca"]
    resultado["cartorio"] = matricula["cartorio"]
    resultado["livro"] = matricula["livro"]
    resultado["folha"] = matricula["folha"]
    resultado["codigo_cartorio"] = matricula["codigo_cartorio"]

    if not matricula["numero"]:
        warnings.append("Matrícula não identificada")

    # =========================================================
    # IMÓVEL
    # =========================================================
    imovel = _resolver_bloco_imovel(dados, warnings)
    resultado["imovel"] = imovel
    resultado["descricao_imovel"] = imovel["descricao"]
    resultado["area_total"] = (imovel.get("area") or {}).get("valor")
    resultado["unidade_area"] = (imovel.get("area") or {}).get("unidade_original")

    # =========================================================
    # PROPRIETÁRIOS
    # =========================================================
    proprietarios = _resolver_proprietarios(dados, warnings)
    resultado["proprietarios"] = proprietarios

    # =========================================================
    # SEGMENTOS
    # =========================================================
    segmentos_validos, erros_segmentos = _resolver_segmentos(dados, warnings)
    erros.extend(erros_segmentos)

    # =========================================================
    # GEOMETRIA
    # =========================================================
    geometria = _resolver_geometria(dados, segmentos_validos, warnings)
    resultado["geometria"] = geometria

    # compatibilidade legado
    resultado["memorial_texto"] = geometria.get("memorial_texto")
    resultado["segmentos_memorial"] = geometria.get("segmentos")
    resultado["geojson"] = geometria.get("geojson")

    # =========================================================
    # CONFRONTANTES
    # =========================================================
    confrontantes = _resolver_confrontantes(dados, warnings)
    resultado["confrontantes"] = confrontantes

    # =========================================================
    # QUALIDADE
    # =========================================================
    score = _calcular_score_qualidade(
        matricula=matricula,
        imovel=imovel,
        proprietarios=proprietarios,
        geometria=geometria,
        confrontantes=confrontantes,
    )

    warnings = _deduplicar_warnings(warnings)

    resultado["qualidade"] = {
        "score": score,
        "erros": erros,
        "warnings": warnings,
    }

    # =========================================================
    # FAIL HARD CONTROLADO
    # =========================================================
    # Regras:
    # 1. Falha dura apenas quando faltar estrutura mínima total.
    # 2. Segmentos inválidos não derrubam se houver memorial_texto ou geojson.
    # 3. Mantém robustez em produção.
    fonte_geometrica = geometria.get("fonte")
    if erros and not fonte_geometrica:
        raise ValueError(f"OCR inválido: {erros}")

    # OCRStructured exige proprietários não vazios; manter isso explícito
    if not proprietarios:
        raise ValueError("OCR inválido: nenhum proprietário válido identificado")

    return resultado