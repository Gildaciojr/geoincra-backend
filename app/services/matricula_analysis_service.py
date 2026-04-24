from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


class MatriculaAnalysisService:
    """
    Serviço responsável por análise jurídica da matrícula.

    NÃO altera dados.
    NÃO persiste automaticamente.
    Apenas analisa e retorna estrutura rica.
    """

    # =========================================================
    # REGEX BASE
    # =========================================================

    REGEX_CPF = r"\d{3}\.\d{3}\.\d{3}-\d{2}"
    REGEX_CNPJ = r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}"

    REGEX_MATRICULA = r"\bmatr[íi]cula\s*n?[ºo]?\s*\d+"
    REGEX_AVERBACAO = r"\bav[-/\s]?\d+\b"
    REGEX_REGISTRO = r"\br[-/\s]?\d+\b"

    PALAVRAS_ONUS = [
        "hipoteca",
        "penhora",
        "usufruto",
        "alienação fiduciária",
        "alienacao fiduciaria",
        "indisponibilidade",
        "ônus real",
        "onus real",
        "arresto",
        "sequestro",
        "servidão",
        "servidao",
        "cláusula resolutiva",
        "clausula resolutiva",
    ]

    PALAVRAS_RISCO = [
        "ação judicial",
        "acao judicial",
        "litígio",
        "litigio",
        "disputa",
        "embargo",
        "irregular",
        "sobreposição",
        "sobreposicao",
        "bloqueio",
        "cancelamento",
        "nulidade",
        "indisponível",
        "indisponivel",
    ]

    TIPOS_ATO_KEYWORDS = {
        "COMPRA_E_VENDA": [
            "compra e venda",
            "venda e compra",
            "transmitente",
            "adquirente",
        ],
        "DOACAO": [
            "doação",
            "doacao",
            "doador",
            "donatário",
            "donatario",
        ],
        "PERMUTA": [
            "permuta",
        ],
        "HIPOTECA": [
            "hipoteca",
            "credor hipotecário",
            "credor hipotecario",
        ],
        "PENHORA": [
            "penhora",
        ],
        "USUFRUTO": [
            "usufruto",
        ],
        "ALIENACAO_FIDUCIARIA": [
            "alienação fiduciária",
            "alienacao fiduciaria",
        ],
        "DESMEMBRAMENTO": [
            "desmembramento",
            "desmembrada",
            "desmembrado",
        ],
        "UNIFICACAO": [
            "unificação",
            "unificacao",
            "unificada",
            "unificado",
        ],
        "RETIFICACAO": [
            "retificação",
            "retificacao",
            "retificada",
            "retificado",
        ],
        "INCRA_CCIR": [
            "incra",
            "ccir",
            "nirf",
            "sncr",
            "car",
        ],
    }

    # =========================================================
    # ENTRYPOINT
    # =========================================================
    @staticmethod
    def analisar(
        texto: Optional[str],
        dados_ocr: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:

        if not texto or not isinstance(texto, str):
            return MatriculaAnalysisService._retorno_vazio("Texto da matrícula ausente")

        texto_normalizado = MatriculaAnalysisService._normalizar_texto(texto)

        # =========================================================
        # EXTRAÇÕES BASE
        # =========================================================
        proprietarios_texto = MatriculaAnalysisService._extrair_proprietarios(
            texto_normalizado
        )

        proprietarios_ocr = MatriculaAnalysisService._extrair_proprietarios_ocr(
            dados_ocr
        )

        proprietarios = MatriculaAnalysisService._merge_proprietarios(
            proprietarios_texto,
            proprietarios_ocr,
        )

        averbacoes = MatriculaAnalysisService._extrair_averbacoes(texto_normalizado)
        registros = MatriculaAnalysisService._extrair_registros(texto_normalizado)
        onus = MatriculaAnalysisService._extrair_onus(texto_normalizado)
        riscos = MatriculaAnalysisService._extrair_riscos(texto_normalizado)

        # =========================================================
        # HISTÓRICO OCR + FALLBACK TEXTO
        # =========================================================
        historico = MatriculaAnalysisService._extrair_historico_ocr(
            dados_ocr=dados_ocr,
            texto=texto_normalizado,
        )

        # =========================================================
        # CADEIA REGISTRAL
        # =========================================================
        cadeia = MatriculaAnalysisService._avaliar_cadeia_registral(historico)

        # =========================================================
        # CLASSIFICAÇÃO
        # =========================================================
        classificacao = MatriculaAnalysisService._classificar_matricula(
            proprietarios=proprietarios,
            onus=onus,
            riscos=riscos,
            cadeia=cadeia,
        )

        # =========================================================
        # SCORE
        # =========================================================
        score = MatriculaAnalysisService._calcular_score(
            proprietarios=proprietarios,
            onus=onus,
            riscos=riscos,
            cadeia=cadeia,
        )

        return {
            "success": True,
            "proprietarios": proprietarios,
            "averbacoes": averbacoes,
            "registros": registros,
            "onus": onus,
            "riscos": riscos,
            "historico": historico,
            "cadeia_registral": cadeia,
            "classificacao": classificacao,
            "score_juridico": score,
        }

    # =========================================================
    # NORMALIZAÇÃO
    # =========================================================
    @staticmethod
    def _normalizar_texto(texto: str) -> str:
        texto = texto.lower()
        texto = re.sub(r"\s+", " ", texto)
        return texto.strip()

    @staticmethod
    def _safe_text(valor: Any) -> Optional[str]:
        if valor is None:
            return None

        texto = " ".join(str(valor).strip().split())
        return texto or None

    @staticmethod
    def _normalizar_codigo_ato(valor: Any) -> Optional[str]:
        texto = MatriculaAnalysisService._safe_text(valor)

        if not texto:
            return None

        texto = texto.upper()
        texto = texto.replace("/", "-")
        texto = re.sub(r"\s+", "", texto)
        texto = re.sub(r"^(R|AV)(\d+)$", r"\1-\2", texto)

        return texto

    @staticmethod
    def _normalizar_tipo_ato(valor: Any, codigo: Optional[str] = None) -> Optional[str]:
        texto = MatriculaAnalysisService._safe_text(valor)

        if texto:
            texto_upper = texto.upper()

            if texto_upper in ["R", "REGISTRO"]:
                return "R"

            if texto_upper in ["AV", "AVERBACAO", "AVERBAÇÃO"]:
                return "AV"

        if codigo:
            codigo_upper = codigo.upper()

            if codigo_upper.startswith("R-"):
                return "R"

            if codigo_upper.startswith("AV-"):
                return "AV"

        return texto.upper() if texto else None

    @staticmethod
    def _extrair_numero_ato(valor: Any, codigo: Optional[str] = None) -> Optional[str]:
        texto = MatriculaAnalysisService._safe_text(valor)

        if texto:
            numeros = re.sub(r"\D", "", texto)
            if numeros:
                return numeros

        if codigo:
            numeros = re.sub(r"\D", "", codigo)
            if numeros:
                return numeros

        return None

    @staticmethod
    def _classificar_tipo_juridico(descricao: Optional[str]) -> Optional[str]:
        if not descricao:
            return None

        texto = MatriculaAnalysisService._normalizar_texto(descricao)

        for tipo, palavras in MatriculaAnalysisService.TIPOS_ATO_KEYWORDS.items():
            for palavra in palavras:
                if palavra in texto:
                    return tipo

        return None

    # =========================================================
    # PROPRIETÁRIOS
    # =========================================================
    @staticmethod
    def _extrair_proprietarios(texto: str) -> List[Dict[str, Any]]:
        proprietarios: List[Dict[str, Any]] = []

        linhas = texto.split(".")

        for linha in linhas:
            if "propriet" not in linha:
                continue

            nome = MatriculaAnalysisService._safe_text(linha)

            if not nome:
                continue

            cpf = re.search(MatriculaAnalysisService.REGEX_CPF, linha)
            cnpj = re.search(MatriculaAnalysisService.REGEX_CNPJ, linha)

            proprietarios.append(
                {
                    "nome": nome[:150],
                    "cpf": cpf.group(0) if cpf else None,
                    "cnpj": cnpj.group(0) if cnpj else None,
                    "cpf_cnpj": cpf.group(0) if cpf else cnpj.group(0) if cnpj else None,
                    "tipo": "pj" if cnpj else "pf",
                    "origem": "texto",
                }
            )

        return proprietarios

    @staticmethod
    def _extrair_proprietarios_ocr(
        dados_ocr: Optional[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        if not dados_ocr or not isinstance(dados_ocr, dict):
            return []

        proprietarios_raw = dados_ocr.get("proprietarios") or []

        if not isinstance(proprietarios_raw, list):
            return []

        proprietarios: List[Dict[str, Any]] = []

        for item in proprietarios_raw:
            if not isinstance(item, dict):
                continue

            nome = MatriculaAnalysisService._safe_text(item.get("nome"))
            cpf_cnpj = MatriculaAnalysisService._safe_text(item.get("cpf_cnpj"))

            if not nome:
                continue

            somente_digitos = re.sub(r"\D", "", str(cpf_cnpj or ""))

            cpf = cpf_cnpj if len(somente_digitos) == 11 else None
            cnpj = cpf_cnpj if len(somente_digitos) == 14 else None

            tipo = item.get("tipo")
            if not tipo:
                tipo = "pj" if cnpj else "pf"

            proprietarios.append(
                {
                    "nome": nome,
                    "cpf": cpf,
                    "cnpj": cnpj,
                    "cpf_cnpj": cpf_cnpj,
                    "tipo": str(tipo).lower(),
                    "origem": "ocr",
                }
            )

        return proprietarios

    @staticmethod
    def _merge_proprietarios(
        proprietarios_texto: List[Dict[str, Any]],
        proprietarios_ocr: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        resultado: List[Dict[str, Any]] = []
        vistos: set[tuple[str, str]] = set()

        for item in proprietarios_ocr + proprietarios_texto:
            nome = MatriculaAnalysisService._safe_text(item.get("nome"))
            cpf_cnpj = MatriculaAnalysisService._safe_text(
                item.get("cpf_cnpj") or item.get("cpf") or item.get("cnpj")
            )

            if not nome:
                continue

            chave = (
                nome.upper(),
                re.sub(r"\D", "", str(cpf_cnpj or "")),
            )

            if chave in vistos:
                continue

            vistos.add(chave)
            resultado.append(item)

        return resultado

    # =========================================================
    # AVERBAÇÕES
    # =========================================================
    @staticmethod
    def _extrair_averbacoes(texto: str) -> List[str]:
        encontrados = re.findall(MatriculaAnalysisService.REGEX_AVERBACAO, texto)

        vistos = set()
        resultado: List[str] = []

        for item in encontrados:
            codigo = MatriculaAnalysisService._normalizar_codigo_ato(item)

            if not codigo:
                continue

            if codigo not in vistos:
                vistos.add(codigo)
                resultado.append(codigo)

        return resultado

    # =========================================================
    # REGISTROS
    # =========================================================
    @staticmethod
    def _extrair_registros(texto: str) -> List[str]:
        encontrados = re.findall(MatriculaAnalysisService.REGEX_REGISTRO, texto)

        vistos = set()
        resultado: List[str] = []

        for item in encontrados:
            codigo = MatriculaAnalysisService._normalizar_codigo_ato(item)

            if not codigo:
                continue

            if codigo not in vistos:
                vistos.add(codigo)
                resultado.append(codigo)

        return resultado

    # =========================================================
    # ÔNUS
    # =========================================================
    @staticmethod
    def _extrair_onus(texto: str) -> List[str]:
        encontrados: List[str] = []

        for palavra in MatriculaAnalysisService.PALAVRAS_ONUS:
            if palavra in texto:
                encontrados.append(palavra)

        return MatriculaAnalysisService._deduplicar_lista(encontrados)

    # =========================================================
    # RISCOS
    # =========================================================
    @staticmethod
    def _extrair_riscos(texto: str) -> List[str]:
        encontrados: List[str] = []

        for palavra in MatriculaAnalysisService.PALAVRAS_RISCO:
            if palavra in texto:
                encontrados.append(palavra)

        return MatriculaAnalysisService._deduplicar_lista(encontrados)

    @staticmethod
    def _deduplicar_lista(valores: List[str]) -> List[str]:
        vistos = set()
        resultado: List[str] = []

        for valor in valores:
            texto = MatriculaAnalysisService._safe_text(valor)

            if not texto:
                continue

            chave = texto.lower()

            if chave in vistos:
                continue

            vistos.add(chave)
            resultado.append(texto)

        return resultado

    # =========================================================
    # HISTÓRICO REGISTRAL
    # =========================================================
    @staticmethod
    def _extrair_historico_ocr(
        dados_ocr: Optional[Dict[str, Any]] = None,
        texto: Optional[str] = None,
    ) -> List[Dict[str, Any]]:

        historico_final: List[Dict[str, Any]] = []

        # =========================================================
        # 1. PRIORIDADE — HISTÓRICO ESTRUTURADO DO OCR
        # =========================================================
        if dados_ocr and isinstance(dados_ocr, dict):
            historico = dados_ocr.get("historico") or {}
            atos_raw = historico.get("atos") if isinstance(historico, dict) else []

            if isinstance(atos_raw, list):
                for item in atos_raw:
                    if not isinstance(item, dict):
                        continue

                    codigo = MatriculaAnalysisService._normalizar_codigo_ato(
                        item.get("codigo")
                    )

                    tipo = MatriculaAnalysisService._normalizar_tipo_ato(
                        item.get("tipo"),
                        codigo=codigo,
                    )

                    numero = MatriculaAnalysisService._extrair_numero_ato(
                        item.get("numero"),
                        codigo=codigo,
                    )

                    descricao = MatriculaAnalysisService._safe_text(
                        item.get("descricao")
                    )

                    texto_original = MatriculaAnalysisService._safe_text(
                        item.get("texto_original")
                    )

                    descricao_base = descricao or texto_original

                    if not codigo:
                        if tipo and numero:
                            codigo = f"{tipo}-{numero}"

                    if not codigo and not descricao_base:
                        continue

                    historico_final.append(
                        {
                            "tipo": tipo,
                            "numero": numero,
                            "codigo": codigo,
                            "descricao": descricao,
                            "data": MatriculaAnalysisService._safe_text(item.get("data")),
                            "protocolo": MatriculaAnalysisService._safe_text(
                                item.get("protocolo")
                            ),
                            "valor": item.get("valor"),
                            "envolvidos": item.get("envolvidos") or [],
                            "texto_original": texto_original,
                            "classificacao_ato": MatriculaAnalysisService._classificar_tipo_juridico(
                                descricao_base
                            ),
                            "origem": "ocr",
                        }
                    )

        # =========================================================
        # 2. FALLBACK — TEXTO DA MATRÍCULA
        # =========================================================
        if texto and isinstance(texto, str):
            encontrados = re.findall(
                r"\b(R|AV)[-/\s]?(\d+)\b",
                texto,
                flags=re.IGNORECASE,
            )

            for tipo_raw, numero_raw in encontrados:
                tipo = tipo_raw.upper()
                numero = str(numero_raw)
                codigo = f"{tipo}-{numero}"

                historico_final.append(
                    {
                        "tipo": tipo,
                        "numero": numero,
                        "codigo": codigo,
                        "descricao": None,
                        "data": None,
                        "protocolo": None,
                        "valor": None,
                        "envolvidos": [],
                        "texto_original": None,
                        "classificacao_ato": None,
                        "origem": "texto",
                    }
                )

        return MatriculaAnalysisService._deduplicar_historico(historico_final)

    @staticmethod
    def _deduplicar_historico(
        historico: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        resultado: List[Dict[str, Any]] = []
        vistos: set[str] = set()

        for ato in historico:
            if not isinstance(ato, dict):
                continue

            codigo = MatriculaAnalysisService._normalizar_codigo_ato(
                ato.get("codigo")
            )

            descricao = MatriculaAnalysisService._safe_text(
                ato.get("descricao") or ato.get("texto_original")
            )

            chave = codigo or descricao

            if not chave:
                continue

            chave = chave.upper()

            if chave in vistos:
                continue

            vistos.add(chave)

            if codigo:
                ato["codigo"] = codigo
                ato["tipo"] = MatriculaAnalysisService._normalizar_tipo_ato(
                    ato.get("tipo"),
                    codigo=codigo,
                )
                ato["numero"] = MatriculaAnalysisService._extrair_numero_ato(
                    ato.get("numero"),
                    codigo=codigo,
                )

            resultado.append(ato)

        try:
            resultado.sort(
                key=lambda x: (
                    0 if x.get("numero") and str(x.get("numero")).isdigit() else 1,
                    int(x.get("numero")) if x.get("numero") and str(x.get("numero")).isdigit() else 999999,
                    str(x.get("codigo") or ""),
                )
            )
        except Exception:
            pass

        return resultado

    # =========================================================
    # CADEIA REGISTRAL
    # =========================================================
    @staticmethod
    def _avaliar_cadeia_registral(
        historico: List[Dict[str, Any]],
    ) -> Dict[str, Any]:

        if not historico:
            return {
                "cadeia_valida": False,
                "total_atos": 0,
                "total_registros": 0,
                "total_averbacoes": 0,
                "sequencia_registros": [],
                "sequencia_averbacoes": [],
                "falhas": ["Histórico registral não identificado"],
            }

        registros: List[int] = []
        averbacoes: List[int] = []
        falhas: List[str] = []

        for ato in historico:
            if not isinstance(ato, dict):
                continue

            tipo = str(ato.get("tipo") or "").upper()
            numero = ato.get("numero")

            numero_str = re.sub(r"\D", "", str(numero or ""))

            if not numero_str:
                continue

            numero_int = int(numero_str)

            if tipo == "R":
                registros.append(numero_int)

            elif tipo == "AV":
                averbacoes.append(numero_int)

        registros_ordenados = sorted(set(registros))
        averbacoes_ordenadas = sorted(set(averbacoes))

        cadeia_valida = True

        if registros and registros != sorted(registros):
            cadeia_valida = False
            falhas.append("Registros fora de ordem sequencial")

        if averbacoes and averbacoes != sorted(averbacoes):
            cadeia_valida = False
            falhas.append("Averbações fora de ordem sequencial")

        if not registros and not averbacoes:
            cadeia_valida = False
            falhas.append("Nenhum R/AV identificado no histórico")

        return {
            "cadeia_valida": cadeia_valida,
            "total_atos": len(historico),
            "total_registros": len(registros_ordenados),
            "total_averbacoes": len(averbacoes_ordenadas),
            "sequencia_registros": registros_ordenados,
            "sequencia_averbacoes": averbacoes_ordenadas,
            "falhas": falhas,
        }

    # =========================================================
    # CLASSIFICAÇÃO
    # =========================================================
    @staticmethod
    def _classificar_matricula(
        proprietarios: List[Any],
        onus: List[str],
        riscos: List[str],
        cadeia: Dict[str, Any],
    ) -> Dict[str, Any]:

        status = "regular"

        if not proprietarios:
            status = "irregular"

        if cadeia and not cadeia.get("cadeia_valida"):
            status = "cadeia_irregular"

        if riscos:
            status = "risco"

        if onus:
            status = "com_onus"

        return {
            "status": status,
            "tem_onus": bool(onus),
            "tem_risco": bool(riscos),
            "cadeia_valida": cadeia.get("cadeia_valida") if cadeia else None,
            "total_atos": cadeia.get("total_atos") if cadeia else 0,
            "total_registros": cadeia.get("total_registros") if cadeia else 0,
            "total_averbacoes": cadeia.get("total_averbacoes") if cadeia else 0,
            "proprietarios_identificados": bool(proprietarios),
        }

    # =========================================================
    # SCORE
    # =========================================================
    @staticmethod
    def _calcular_score(
        proprietarios: List[Any],
        onus: List[str],
        riscos: List[str],
        cadeia: Dict[str, Any],
    ) -> int:

        score = 100

        if not proprietarios:
            score -= 30

        if onus:
            score -= 20

        if riscos:
            score -= 30

        if not cadeia.get("cadeia_valida"):
            score -= 15

        total_atos = cadeia.get("total_atos", 0)

        if total_atos == 0:
            score -= 15
        elif total_atos < 2:
            score -= 10
        elif total_atos < 4:
            score -= 5

        return max(score, 0)

    # =========================================================
    # FALLBACK
    # =========================================================
    @staticmethod
    def _retorno_vazio(msg: str) -> Dict[str, Any]:
        return {
            "success": False,
            "message": msg,
            "proprietarios": [],
            "averbacoes": [],
            "registros": [],
            "onus": [],
            "riscos": [],
            "historico": [],
            "cadeia_registral": {
                "cadeia_valida": False,
                "total_atos": 0,
                "total_registros": 0,
                "total_averbacoes": 0,
                "sequencia_registros": [],
                "sequencia_averbacoes": [],
                "falhas": [msg],
            },
            "classificacao": {},
            "score_juridico": 0,
        }