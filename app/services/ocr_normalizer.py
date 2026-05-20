from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from app.services.memorial_parser_service import MemorialParserService


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

def _extrair_matricula_do_texto(texto: Optional[str]) -> Optional[str]:
    if not texto:
        return None

    texto = str(texto)

    match = re.search(
        r"(?i)(?:matr[íi]cula\s*(?:n[ºo°]?\s*)?)?(\d{2,6}[./-]?\d{0,6})",
        texto
    )

    if match:
        return _normalizar_matricula(match.group(1))

    return None


def _extrair_direcao_do_texto(texto: Optional[str]) -> Optional[str]:
    if not texto:
        return None

    texto_upper = _normalizar_texto_upper_sem_acentos(texto)

    if not texto_upper:
        return None

    if "NORTE" in texto_upper:
        return "N"
    if "SUL" in texto_upper:
        return "S"
    if "LESTE" in texto_upper:
        return "E"
    if "OESTE" in texto_upper:
        return "W"

    return None


def _limpar_descricao_confrontante(descricao: Optional[str]) -> Optional[str]:
    if not descricao:
        return None

    texto = descricao

    texto = re.sub(r"(?i)matr[íi]cula\s*n[ºo°]?\s*\d+[./-]?\d*", "", texto)
    texto = re.sub(r"\s{2,}", " ", texto)

    return texto.strip() or None


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


def _geojson_tem_geometria_valida(geojson: Any) -> bool:
    if not isinstance(geojson, dict):
        return False

    tipo = geojson.get("type")

    if tipo in {"Polygon", "MultiPolygon"}:
        return isinstance(geojson.get("coordinates"), list) and bool(geojson.get("coordinates"))

    if tipo == "Feature":
        return _geojson_tem_geometria_valida(geojson.get("geometry"))

    if tipo == "FeatureCollection":
        features = geojson.get("features")
        if not isinstance(features, list):
            return False

        return any(
            _geojson_tem_geometria_valida(feature)
            for feature in features
            if isinstance(feature, dict)
        )

    geometry = geojson.get("geometry")
    if isinstance(geometry, dict):
        return _geojson_tem_geometria_valida(geometry)

    return False


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


def _inferir_tipo_confrontante(
    nome: Optional[str],
    descricao: Optional[str],
    identificacao: Optional[str],
) -> Optional[str]:

    base = " ".join(
        part for part in [nome, descricao, identificacao] if part
    ).lower()

    if not base:
        return None

    if any(t in base for t in ["estrada", "rodovia", "vicinal", "via municipal"]):
        return "estrada"

    if any(t in base for t in ["rio", "córrego", "corrego", "ribeirão", "ribeirao", "curso d'água", "curso dagua"]):
        return "curso_dagua"

    if any(t in base for t in ["área pública", "area publica", "patrimônio público", "patrimonio publico"]):
        return "area_publica"

    if "reserva legal" in base:
        return "reserva_legal"

    if any(t in base for t in ["fazenda", "sítio", "sitio", "chácara", "chacara", "lote", "gleba", "quinhão", "quinhao"]):
        return "imovel_rural"

    if any(t in base for t in ["matrícula", "matricula", "transcrição", "transcricao"]):
        return "imovel_registrado"

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

    area_dict = _first_dict(imovel_dict.get("area") if imovel_dict else None)

    area_raw = _coalesce(
        dados.get("area_total"),
        imovel_dict.get("area_total") if imovel_dict else None,
        imovel_dict.get("area") if imovel_dict else None,
        area_dict.get("valor") if area_dict else None,
    )

    unidade_raw = _coalesce(
        dados.get("unidade_area"),
        imovel_dict.get("unidade_area") if imovel_dict else None,
        area_dict.get("unidade_original") if area_dict else None,
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

        # =========================================================
        # 🔥 AZIMUTE / RUMO — NORMALIZAÇÃO OCR-SAFE
        # =========================================================

        azimute_raw = _normalizar_texto(
            _coalesce(
                s.get("azimute_raw"),
                s.get("azimute"),
                s.get("rumo"),
                s.get("bearing"),
                s.get("angulo"),
                s.get("direcao"),
                s.get("valor"),
                s.get("azimute_decimal"),
            )
        )

        # =========================================================
        # 🔥 FALLBACK BASEADO NO TIPO
        # =========================================================

        if not azimute_raw:
            tipo = str(s.get("tipo") or "").lower()

            if tipo == "azimute_decimal":
                val = _coalesce(
                    s.get("valor"),
                    s.get("azimute"),
                )

                if val is not None:
                    azimute_raw = _normalizar_texto(val)

            elif tipo == "azimute":
                val = _coalesce(
                    s.get("rumo"),
                    s.get("valor"),
                )

                if val:
                    azimute_raw = _normalizar_texto(val)

            elif tipo == "cartorio_metros":
                val = _coalesce(
                    s.get("rumo"),
                    s.get("descricao"),
                )

                if val:
                    azimute_raw = _normalizar_texto(val)

        # =========================================================
        # 🔥 SANITIZAÇÃO OCR GEOMÉTRICA
        # =========================================================

        if azimute_raw:

            az_original = azimute_raw

            azimute_raw = (
                azimute_raw
                .replace("º", "°")
                .replace("˚", "°")
                .replace("o", "°")
                .replace("O", "°")
                .replace("’", "'")
                .replace("`", "'")
                .replace("´", "'")
                .replace("“", '"')
                .replace("”", '"')
            )

            azimute_raw = re.sub(
                r"\s+",
                " ",
                azimute_raw,
            ).strip()

            # =====================================================
            # 🔥 OCR COLAPSADO
            # EX:
            # 9195040
            # 905030
            # 1795959
            # =====================================================

            somente_numeros = re.sub(
                r"\D",
                "",
                azimute_raw,
            )

            possui_dms = any(
                token in azimute_raw
                for token in ["°", "'", '"']
            )

            possui_quadrante = bool(
                re.search(r"[NS].*[EW]", azimute_raw.upper())
            )

            # =====================================================
            # 🔥 RECONSTRUÇÃO DMS AUTOMÁTICA
            # =====================================================

            if (
                not possui_dms
                and not possui_quadrante
                and somente_numeros.isdigit()
                and len(somente_numeros) in {6, 7}
            ):

                try:

                    if len(somente_numeros) == 6:
                        graus = somente_numeros[:2]
                        minutos = somente_numeros[2:4]
                        segundos = somente_numeros[4:6]

                    else:
                        graus = somente_numeros[:3]
                        minutos = somente_numeros[3:5]
                        segundos = somente_numeros[5:7]

                    graus_int = int(graus)
                    minutos_int = int(minutos)
                    segundos_int = int(segundos)

                    if (
                        0 <= graus_int <= 360
                        and 0 <= minutos_int < 60
                        and 0 <= segundos_int < 60
                    ):
                        azimute_raw = (
                            f"{graus_int}°"
                            f"{minutos_int}'"
                            f'{segundos_int}"'
                        )

                except Exception:
                    azimute_raw = az_original

            # =====================================================
            # 🔥 VALIDAÇÃO PREVENTIVA
            # =====================================================

            try:

                az_decimal = (
                    MemorialParserService
                    ._parse_azimute_ou_rumo(azimute_raw)
                )

                if az_decimal < 0 or az_decimal > 360:
                    raise ValueError(
                        "Azimute fora do intervalo válido"
                    )

            except Exception:

                erros.append(
                    f"Segmento {i} inválido: "
                    f"ângulo OCR inválido ({az_original})"
                )

                continue

        # =========================================================
        # DISTÂNCIA
        # =========================================================
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

        # =========================================================
        # VALIDAÇÕES (MANTIDAS)
        # =========================================================
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

    # =========================================================
    # NOVO BLOCO — USAR MEMORIAL SE NECESSÁRIO (MANTIDO + SEGURO)
    # =========================================================
    if not segmentos or len(segmentos) < 3:
        geometria_dict = _first_dict(dados.get("geometria"))

        memorial_texto = _normalizar_memorial_texto(
            _coalesce(
                dados.get("memorial_texto"),
                geometria_dict.get("memorial_texto") if geometria_dict else None,
            )
        )

        if memorial_texto:
            try:
                segmentos_extraidos = MemorialParserService.extrair_segmentos(memorial_texto)

                if segmentos_extraidos and len(segmentos_extraidos) >= 3:
                    warnings.append("Segmentos gerados automaticamente a partir do memorial descritivo")

                    segmentos = []
                    for seg in segmentos_extraidos:
                        az = _normalizar_texto(
                            _coalesce(
                                seg.get("azimute_raw"),
                                seg.get("rumo"),
                                seg.get("azimute"),
                            )
                        )

                        dist = _to_float(seg.get("distancia"))

                        if not az or dist is None or dist <= 0:
                            continue

                        novo_seg: Dict[str, Any] = {
                            "azimute_raw": az,
                            "distancia": float(dist),
                        }

                        if seg.get("ordem") is not None:
                            novo_seg["ordem"] = seg.get("ordem")

                        if seg.get("vertice_inicial"):
                            novo_seg["vertice_inicial"] = seg.get("vertice_inicial")

                        if seg.get("vertice_final"):
                            novo_seg["vertice_final"] = seg.get("vertice_final")

                        segmentos.append(novo_seg)

                else:
                    warnings.append("Memorial não gerou segmentos suficientes")

            except Exception as e:
                warnings.append(f"Falha ao extrair segmentos do memorial: {str(e)}")

    # =========================================================
    # REGRA ORIGINAL (MANTIDA)
    # =========================================================
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

    geojson_existente = _normalizar_geojson(
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
    geojson: Optional[Dict[str, Any]] = geojson_existente

    # =========================================================
    # TENTAR GERAR GEOMETRIA A PARTIR DOS SEGMENTOS
    # =========================================================
    if segmentos_validos and len(segmentos_validos) >= 3:
        try:
            texto_base = (
                memorial_texto or ""
            ).strip()

            if texto_base:

                geometria_gerada = (
                    MemorialParserService
                    .gerar_geometria(
                        texto_base
                    )
                )

            else:
                geometria_gerada = None

            if (
                geometria_gerada
                and isinstance(geometria_gerada, dict)
                and geometria_gerada.get("geojson")
            ):
                novo_geojson = geometria_gerada.get("geojson")

                if novo_geojson:
                    geojson = novo_geojson
                    segmentos_validos = geometria_gerada.get("segmentos") or segmentos_validos
                    fonte = "segmentos_processados"

        except Exception as e:
            warnings.append(f"Falha ao gerar geometria via segmentos: {str(e)}")

    # =========================================================
    # FALLBACK: GERAR VIA MEMORIAL
    # =========================================================
    if not fonte and memorial_texto:
        try:
            geometria_gerada = MemorialParserService.gerar_geometria(memorial_texto)

            if (
                geometria_gerada
                and isinstance(geometria_gerada, dict)
                and geometria_gerada.get("geojson")
            ):
                novo_geojson = geometria_gerada.get("geojson")

                if novo_geojson:
                    geojson = novo_geojson
                    segmentos_validos = geometria_gerada.get("segmentos") or segmentos_validos
                    fonte = "memorial_processado"

        except Exception as e:
            warnings.append(f"Falha ao gerar geometria via memorial: {str(e)}")

    # =========================================================
    # FALLBACK FINAL: GEOJSON EXISTENTE
    # =========================================================
    if not fonte and geojson_existente:
        geojson = geojson_existente
        fonte = "geojson"

    # =========================================================
    # NORMALIZAÇÃO FINAL DO GEOJSON (CRÍTICO)
    # =========================================================
    if geojson and isinstance(geojson, dict):
        tipo_geojson = geojson.get("type")

        if tipo_geojson in {"Polygon", "MultiPolygon", "FeatureCollection"}:
            pass

        elif tipo_geojson == "Feature":
            geojson = {
                "type": "FeatureCollection",
                "features": [geojson],
            }

        elif isinstance(geojson.get("geometry"), dict):

            geojson = {
                "type": "Feature",
                "geometry": geojson.get("geometry"),
                "properties": geojson.get("properties", {}),
            }

            geojson = {
                "type": "FeatureCollection",
                "features": [geojson],
            }

    # =========================================================
    # NENHUMA FONTE
    # =========================================================
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

    def _extrair_matricula_forte(*valores: Any) -> Optional[str]:
        for valor in valores:
            texto = _normalizar_texto(valor)

            if not texto:
                continue

            candidatos = [
                r"(?i)\bmatr[íi]cula\s*(?:n[ºo°.]?\s*)?[:\-]?\s*(\d{1,3}(?:[.\-/]\d{3})+|\d{3,8})",
                r"(?i)\bmat\.?\s*(?:n[ºo°.]?\s*)?[:\-]?\s*(\d{1,3}(?:[.\-/]\d{3})+|\d{3,8})",
                r"(?i)\bregistro\s*(?:n[ºo°.]?\s*)?[:\-]?\s*(\d{1,3}(?:[.\-/]\d{3})+|\d{3,8})",
                r"(?i)\btranscri[cç][aã]o\s*(?:n[ºo°.]?\s*)?[:\-]?\s*(\d{1,3}(?:[.\-/]\d{3})+|\d{3,8})",
                r"(?i)\b(?:R|AV)[\-. ]?\d+\s*[\-/]\s*(\d{1,3}(?:[.\-/]\d{3})+|\d{3,8})",
                r"(?i)\bM[\-. ]?(\d{1,3}(?:[.\-/]\d{3})+|\d{3,8})\b",
                r"(?i)\bsob\s+(?:a\s+)?(?:matr[íi]cula|mat\.?)\s*(?:n[ºo°.]?\s*)?[:\-]?\s*(\d{1,3}(?:[.\-/]\d{3})+|\d{3,8})",
            ]

            for pattern in candidatos:
                match = re.search(pattern, texto)

                if match:
                    matricula = _normalizar_matricula(match.group(1))

                    if matricula and len(_somente_digitos(matricula)) >= 3:
                        return matricula

        return None

    def _extrair_direcao_forte(*valores: Any) -> tuple[Optional[str], Optional[str]]:
        for valor in valores:
            texto = _normalizar_texto_upper_sem_acentos(valor)
            if not texto:
                continue

            padroes = [
                ("NORTE", "N"),
                ("SUL", "S"),
                ("LESTE", "E"),
                ("OESTE", "W"),
                ("NORDESTE", "NE"),
                ("NOROESTE", "NW"),
                ("SUDESTE", "SE"),
                ("SUDOESTE", "SW"),
            ]

            for original, normalizado in padroes:
                if original in texto:
                    return original, normalizado

            direcao = _normalizar_direcao(texto)
            if direcao:
                return _normalizar_lado_original(direcao), direcao

        return None, None

    def _limpar_identificacao(
        valor: Any,
        nome_ref: Optional[str],
        descricao_ref: Optional[str],
    ) -> Optional[str]:

        identificacao = _normalizar_identificacao_generica(
            valor
        )

        if not identificacao:
            return None

        if nome_ref and identificacao == nome_ref:
            return None

        if descricao_ref and identificacao == descricao_ref:
            return None

        return identificacao

    def _extrair_proprietario_confrontante(
        texto: Optional[str],
    ) -> Optional[str]:

        texto_norm = _normalizar_texto(texto)

        if not texto_norm:
            return None

        patterns = [
            r"(?i)de propriedade de\s+([^,.;\n]+)",
            r"(?i)propriet[aá]rio:\s*([^,.;\n]+)",
            r"(?i)pertencente a\s+([^,.;\n]+)",
            r"(?i)dom[ií]nio de\s+([^,.;\n]+)",
        ]

        for pattern in patterns:

            match = re.search(
                pattern,
                texto_norm,
            )

            if match:

                nome = _normalizar_texto(
                    match.group(1)
                )

                if nome and len(nome) >= 3:
                    return nome

        return None

    for i, c in enumerate(confrontantes_raw, start=1):

        if isinstance(c, str):
            descricao_original = _normalizar_texto(c)

            if not descricao_original:
                warnings.append(f"Confrontante {i} ignorado (string vazia)")
                continue

            extraidos = _extrair_lote_gleba_de_texto(descricao_original)
            lado_original, lado_normalizado = _extrair_direcao_forte(descricao_original)
            matricula_confrontante = _extrair_matricula_forte(descricao_original)
            descricao_limpa = _limpar_descricao_confrontante(descricao_original) or descricao_original

            confrontantes.append(
                {
                    "lado": lado_original,
                    "lado_normalizado": lado_normalizado,
                    "direcao": lado_normalizado or lado_original,
                    "nome": None,
                    "descricao": descricao_limpa,
                    "matricula": matricula_confrontante,
                    "identificacao": descricao_original,
                    "cpf_cnpj": _normalizar_cpf_cnpj(descricao_original),
                    "tipo": _normalizar_texto_upper_sem_acentos(
                        _inferir_tipo_confrontante(None, descricao_limpa, descricao_original)
                    ),
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
                c.get("proprietario"),
                c.get("proprietario_confrontante"),
            )
        )

        descricao_original = _normalizar_texto(
            _coalesce(
                c.get("descricao"),
                c.get("descricao_completa"),
                c.get("texto"),
                c.get("texto_original"),
            )
        )

        matricula_confrontante = _extrair_matricula_forte(
            c.get("matricula"),
            c.get("numero_matricula"),
            c.get("matricula_confrontante"),
            descricao_original,
            nome,
        )

        cpf_cnpj = _normalizar_cpf_cnpj(
            _coalesce(
                c.get("cpf_cnpj"),
                c.get("cpf"),
                c.get("cnpj"),
                descricao_original,
                nome,
            )
        )

        identificacao_raw = _coalesce(
            c.get("identificacao"),
            c.get("identificacao_imovel"),
            c.get("imovel"),
            c.get("nome_imovel"),
            c.get("fazenda"),
            c.get("sitio"),
            c.get("gleba_descricao"),
        )

        identificacao = _limpar_identificacao(
            identificacao_raw,
            nome_ref=nome,
            descricao_ref=descricao_original,
        )

        proprietario_confrontante = (
            _extrair_proprietario_confrontante(
                descricao_original
            )
        )

        if not identificacao:

            identificacao = (
                _normalizar_identificacao_generica(
                    descricao_original
                )
            )

        extraidos_nome = (
            _extrair_lote_gleba_de_texto(nome)
        )

        extraidos_descricao = (
            _extrair_lote_gleba_de_texto(
                descricao_original
            )
        )

        extraidos_identificacao = (
            _extrair_lote_gleba_de_texto(
                identificacao
            )
        )

        lote = _normalizar_texto(
            _coalesce(
                c.get("lote"),
                extraidos_nome.get("lote"),
                extraidos_descricao.get("lote"),
                extraidos_identificacao.get("lote"),
            )
        )

        gleba = _normalizar_texto(
            _coalesce(
                c.get("gleba"),
                extraidos_nome.get("gleba"),
                extraidos_descricao.get("gleba"),
                extraidos_identificacao.get("gleba"),
            )
        )

        vinculo_registral = None

        base_registral = " ".join(
            part
            for part in [
                nome,
                descricao_original,
                identificacao,
            ]
            if part
        ).lower()

        if "desmembrad" in base_registral:
            vinculo_registral = "DESMEMBRAMENTO"

        elif "remembrad" in base_registral:
            vinculo_registral = "REMEMBRAMENTO"

        elif "originad" in base_registral:
            vinculo_registral = "ORIGEM_MATRICULA"

        elif "parte da matrícula" in base_registral:
            vinculo_registral = "PARTE_MATRICULA"

        elif "objeto da matrícula" in base_registral:
            vinculo_registral = "OBJETO_MATRICULA"

        tipo = _normalizar_texto_upper_sem_acentos(
            _coalesce(
                c.get("tipo"),
                _inferir_tipo_confrontante(
                    nome,
                    descricao_original,
                    identificacao,
                ),
            )
        )

        lado_original, lado_normalizado = (
            _extrair_direcao_forte(
                lado_bruto,
                descricao_original,
                identificacao,
            )
        )

        descricao = (
            _limpar_descricao_confrontante(
                descricao_original
            )
        )

        if not descricao:

            partes_fallback: List[str] = []

            if nome:
                partes_fallback.append(nome)

            if identificacao and identificacao != nome:
                partes_fallback.append(
                    identificacao
                )

            if matricula_confrontante:
                partes_fallback.append(
                    f"Matrícula {matricula_confrontante}"
                )

            if lote:
                partes_fallback.append(
                    f"Lote {lote}"
                )

            if gleba:
                partes_fallback.append(
                    f"Gleba {gleba}"
                )

            descricao = (
                " / ".join(partes_fallback)
                if partes_fallback
                else None
            )

        if not identificacao:

            identificacao = (
                _normalizar_identificacao_generica(
                    _coalesce(
                        c.get("identificacao_imovel"),
                        c.get("imovel"),
                        c.get("nome_imovel"),
                        descricao_original
                        if not nome
                        else None,
                    )
                )
            )

        nome = _normalizar_texto(nome)
        identificacao = _normalizar_texto(identificacao)
        descricao = _normalizar_texto(descricao)
        matricula_confrontante = _normalizar_matricula(matricula_confrontante)

        if not any([nome, descricao, matricula_confrontante, identificacao, lote, gleba, tipo]):
            warnings.append(
                f"Confrontante {i} ignorado (sem conteúdo útil após normalização)"
            )
            continue

        confrontantes.append(
            {
                "lado": lado_original,
                "lado_normalizado": lado_normalizado,
                "direcao": lado_normalizado or lado_original,
                "nome": nome,
                "descricao": descricao,
                "matricula": matricula_confrontante,
                "identificacao": identificacao,
                "cpf_cnpj": cpf_cnpj,
                "proprietario_confrontante": (
                    proprietario_confrontante
                ),

                "vinculo_registral": (
                    vinculo_registral
                ),
                "tipo": tipo,
                "lote": lote,
                "gleba": gleba,
            }
        )

    confrontantes = _deduplicar_confrontantes(
        confrontantes
    )

    if not confrontantes:
        warnings.append(
            "Nenhum confrontante válido identificado"
        )

    return confrontantes



def _resolver_historico(
    dados: Dict[str, Any],
    warnings: List[str],
) -> Dict[str, Any]:

    historico_raw = dados.get("historico") or {}

    atos_raw = (
        historico_raw.get("atos")
        if isinstance(historico_raw, dict)
        else None
    ) or []

    atos_normalizados: List[Dict[str, Any]] = []

    for i, ato in enumerate(atos_raw, start=1):

        if not isinstance(ato, dict):
            warnings.append(
                f"Ato {i} ignorado (estrutura inválida)"
            )
            continue

        texto_original = _normalizar_texto(
            _coalesce(
                ato.get("texto_original"),
                ato.get("descricao"),
                ato.get("texto"),
            )
        )

        codigo = _normalizar_texto(
            ato.get("codigo")
        )

        tipo = _normalizar_texto_upper_sem_acentos(
            ato.get("tipo")
        )

        numero = _normalizar_texto(
            ato.get("numero")
        )

        # =====================================================
        # 🔥 RECUPERAÇÃO OCR DE CÓDIGO REGISTRAL
        # =====================================================
        if not codigo and texto_original:

            match_codigo = re.search(
                r"(?i)\b(R|AV)[\-. ]?(\d+)\b",
                texto_original,
            )

            if match_codigo:

                tipo_extraido = (
                    match_codigo.group(1)
                    .upper()
                )

                numero_extraido = (
                    match_codigo.group(2)
                )

                codigo = (
                    f"{tipo_extraido}-{numero_extraido}"
                )

                if not tipo:
                    tipo = tipo_extraido

                if not numero:
                    numero = numero_extraido

        # =====================================================
        # 🔥 INFERÊNCIA SEMÂNTICA DE TIPO
        # =====================================================
        if not tipo and texto_original:

            texto_lower = texto_original.lower()

            if "averba" in texto_lower:
                tipo = "AV"

            elif any(
                token in texto_lower
                for token in [
                    "registro",
                    "compra e venda",
                    "transfer",
                    "doa",
                    "cess",
                ]
            ):
                tipo = "R"

        descricao = _normalizar_texto(
            _coalesce(
                ato.get("descricao"),
                texto_original,
            )
        )

        data = _normalizar_texto(
            ato.get("data")
        )

        protocolo = _normalizar_texto(
            ato.get("protocolo")
        )

        valor = _to_float(
            ato.get("valor")
        )

        # =====================================================
        # 🔥 EXTRAÇÃO OCR-SAFE DE DATA
        # =====================================================
        if not data and texto_original:

            match_data = re.search(
                r"\b(\d{2}/\d{2}/\d{4})\b",
                texto_original,
            )

            if match_data:
                data = match_data.group(1)

        # =====================================================
        # 🔥 EXTRAÇÃO OCR-SAFE DE PROTOCOLO
        # =====================================================
        if not protocolo and texto_original:

            match_protocolo = re.search(
                r"(?i)\bprotocolo\s*(?:n[ºo°.]?\s*)?[:\-]?\s*([a-z0-9.\-/]+)",
                texto_original,
            )

            if match_protocolo:
                protocolo = (
                    match_protocolo.group(1)
                )

        envolvidos_raw = (
            ato.get("envolvidos")
            or []
        )

        envolvidos: List[
            Dict[str, Optional[str]]
        ] = []

        # =====================================================
        # 🔥 ENVOLVIDOS ESTRUTURADOS
        # =====================================================
        if isinstance(envolvidos_raw, list):

            for p in envolvidos_raw:

                if not isinstance(p, dict):
                    continue

                nome = _normalizar_texto(
                    p.get("nome")
                )

                cpf_cnpj = (
                    _normalizar_cpf_cnpj(
                        p.get("cpf_cnpj")
                    )
                )

                if not nome:
                    continue

                envolvidos.append(
                    {
                        "nome": nome,
                        "cpf_cnpj": cpf_cnpj,
                    }
                )

        # =====================================================
        # 🔥 EXTRAÇÃO AUTOMÁTICA VIA TEXTO
        # =====================================================
        if (
            not envolvidos
            and texto_original
        ):

            patterns = [
                r"(?i)em favor de\s+([^,.;\n]+)",
                r"(?i)para\s+([^,.;\n]+)",
                r"(?i)por\s+([^,.;\n]+)",
                r"(?i)adquirido por\s+([^,.;\n]+)",
                r"(?i)transmitido a\s+([^,.;\n]+)",
            ]

            nomes_extraidos: List[str] = []

            for pattern in patterns:

                for match in re.finditer(
                    pattern,
                    texto_original,
                ):

                    nome_extraido = (
                        _normalizar_texto(
                            match.group(1)
                        )
                    )

                    if (
                        nome_extraido
                        and len(nome_extraido) >= 4
                    ):
                        nomes_extraidos.append(
                            nome_extraido
                        )

            nomes_unicos = []

            for nome_extraido in nomes_extraidos:

                if nome_extraido not in nomes_unicos:
                    nomes_unicos.append(
                        nome_extraido
                    )

            for nome_extraido in nomes_unicos:

                envolvidos.append(
                    {
                        "nome": nome_extraido,
                        "cpf_cnpj": None,
                    }
                )

        # =====================================================
        # 🔥 FILTRO MÍNIMO
        # =====================================================
        if (
            not codigo
            and not descricao
            and not texto_original
        ):
            warnings.append(
                f"Ato {i} ignorado "
                "(sem conteúdo útil)"
            )
            continue

        atos_normalizados.append(
            {
                "tipo": tipo,
                "numero": numero,
                "codigo": codigo,
                "descricao": descricao,
                "data": data,
                "protocolo": protocolo,
                "valor": valor,
                "envolvidos": envolvidos,
                "texto_original": texto_original,
            }
        )

    # 🔒 ordenação opcional (se tiver número)
    try:
        atos_normalizados.sort(
            key=lambda x: int(re.sub(r"\D", "", x.get("numero") or "0"))
        )
    except Exception:
        pass

    if not atos_normalizados:
        warnings.append("Nenhum histórico registral identificado")

    return {
        "atos": atos_normalizados
    }


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

    # 🔥 VALIDAÇÃO ROBUSTA DO GEOJSON
    geojson_valido = _geojson_tem_geometria_valida(geojson)

    # 🔥 AVALIAÇÃO DE GEOMETRIA MAIS INTELIGENTE
    if not segmentos and not memorial_texto and not geojson_valido:
        score -= 35
    elif not segmentos:
        score -= 10

    # 🔥 PENALIDADE EXTRA PARA GEOJSON INVÁLIDO/Vazio
    if geojson and not geojson_valido:
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
        erros.append("Matrícula ausente")
    else:
        if len(str(matricula["numero"])) < 3:
            warnings.append("Matrícula com formato suspeito")

    # =========================================================
    # IMÓVEL
    # =========================================================
    imovel = _resolver_bloco_imovel(dados, warnings)
    resultado["imovel"] = imovel
    resultado["descricao_imovel"] = imovel["descricao"]
    resultado["area_total"] = (imovel.get("area") or {}).get("valor")
    resultado["unidade_area"] = (imovel.get("area") or {}).get("unidade_original")

    # 🔥 NOVO (CRÍTICO): padronização definitiva da área em hectares
    resultado["area_hectares"] = (imovel.get("area") or {}).get("hectares")

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

    if not confrontantes:
        warnings.append("Sem confrontantes identificados")

    elif len(confrontantes) < 2:
         warnings.append("Poucos confrontantes identificados")

    # =========================================================
    # HISTÓRICO REGISTRAL (NOVO)
    # =========================================================
    historico = _resolver_historico(dados, warnings)
    resultado["historico"] = historico

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


    # =========================================================
    # 🔥 AJUSTES AVANÇADOS DE QUALIDADE
    # =========================================================

    # área crítica
    if not resultado.get("area_hectares"):
      score -= 10


    # confrontantes críticos
    if not confrontantes:
      score -= 15


    # geometria crítica
    if (
     not geometria.get("segmentos")
     and not geometria.get("memorial_texto")
     and not geometria.get("geojson")
    ):
     score -= 20


    # direções incompletas
    if any(not c.get("direcao") for c in confrontantes):
     score -= 5


    # =========================================================
    # 🔥 NOVO — HISTÓRICO REGISTRAL (CRÍTICO)
    # =========================================================
    historico_atos = historico.get("atos") if isinstance(historico, dict) else []


    if not historico_atos:
     score -= 10
     warnings.append("Histórico registral não identificado")


    elif len(historico_atos) < 2:
      score -= 5

      warnings.append("Histórico registral muito raso")

    # =========================================================
    # NORMALIZA SCORE
    # =========================================================
    score = max(score, 0)

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
    if (
        erros
        and not fonte_geometrica
        and not confrontantes
        and not historico_atos
    ):
        raise ValueError(
            f"OCR inválido: {erros}"
        )
    

    # 🔥 NOVO — FAIL HARD POR BAIXA QUALIDADE
    if (
        score < 25
        and not geometria.get("fonte")
        and not confrontantes
    ):
        raise ValueError(
            f"OCR inválido: qualidade muito baixa ({score})"
        )


    # OCRStructured exige proprietários não vazios; manter isso explícito
    if not proprietarios:
        raise ValueError("OCR inválido: nenhum proprietário válido identificado")

    return resultado


# =========================================================
# NORMALIZADORES ESPECÍFICOS POR PROMPT
# =========================================================
def normalizar_documento_bruto(
    dados: Dict[str, Any],
) -> Dict[str, Any]:

    if not isinstance(dados, dict):
        raise ValueError(
            "Documento bruto inválido."
        )

    return {
        "documento_bruto": dados,
        "payload_original": dados,
    }


def normalizar_documento_pessoal(
    dados: Dict[str, Any],
) -> Dict[str, Any]:

    if not isinstance(dados, dict):
        raise ValueError(
            "Documento pessoal inválido."
        )

    pessoa = {
        "nome": _normalizar_texto(
            _coalesce(
                dados.get("nome"),
                dados.get("nome_completo"),
                dados.get("titular"),
            )
        ),

        "cpf": _normalizar_cpf_cnpj(
            _coalesce(
                dados.get("cpf"),
                dados.get("cpf_cnpj"),
            )
        ),

        "rg": _normalizar_texto(
            dados.get("rg")
        ),

        "nascimento": _normalizar_texto(
            dados.get("data_nascimento")
        ),
    }

    documentos = {
        "cpf": pessoa.get("cpf"),
        "rg": pessoa.get("rg"),
    }

    return {
        "pessoa": pessoa,
        "documentos": documentos,
        "payload_original": dados,
    }


def normalizar_ficha_sig(
    dados: Dict[str, Any],
) -> Dict[str, Any]:

    if not isinstance(dados, dict):
        raise ValueError(
            "Ficha SIG inválida."
        )

    ficha = {
        "codigo_imovel": _normalizar_texto(
            _coalesce(
                dados.get("codigo_imovel"),
                dados.get("codigo"),
            )
        ),

        "denominacao": _normalizar_texto(
            _coalesce(
                dados.get("denominacao"),
                dados.get("nome_imovel"),
            )
        ),

        "municipio": _normalizar_texto(
            dados.get("municipio")
        ),

        "area_ha": _to_float(
            _coalesce(
                dados.get("area_ha"),
                dados.get("area"),
            )
        ),
    }

    return {
        "ficha_cadastral": ficha,
        "payload_original": dados,
    }


def normalizar_confrontantes_croqui(
    dados: Dict[str, Any],
) -> Dict[str, Any]:

    if not isinstance(dados, dict):
        raise ValueError(
            "Confrontantes inválidos."
        )

    warnings: List[str] = []

    confrontantes = _resolver_confrontantes(
        dados,
        warnings,
    )

    return {
        "confrontantes": confrontantes,
        "warnings": warnings,
        "payload_original": dados,
    }


def normalizar_memorial_ocr(
    dados: Dict[str, Any],
) -> Dict[str, Any]:

    if not isinstance(dados, dict):
        raise ValueError(
            "Memorial OCR inválido."
        )

    warnings: List[str] = []

    segmentos, erros = _resolver_segmentos(
        dados,
        warnings,
    )

    geometria = _resolver_geometria(
        dados=dados,
        segmentos_validos=segmentos,
        warnings=warnings,
    )

    return {
        "memorial_texto": geometria.get(
            "memorial_texto"
        ),

        "segmentos_memorial": segmentos,

        "geojson": geometria.get(
            "geojson"
        ),

        "warnings": warnings,

        "errors": erros,

        "payload_original": dados,
    }
