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
    REGEX_AVERBACAO = r"\bav[-\s]?\d+\b"
    REGEX_REGISTRO = r"\br[-\s]?\d+\b"

    PALAVRAS_ONUS = [
        "hipoteca",
        "penhora",
        "usufruto",
        "alienação fiduciária",
        "indisponibilidade",
        "ônus real",
    ]

    PALAVRAS_RISCO = [
        "ação judicial",
        "litígio",
        "disputa",
        "embargo",
        "irregular",
        "sobreposição",
    ]

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
        # EXTRAÇÕES BASE (LEGADO)
        # =========================================================
        proprietarios = MatriculaAnalysisService._extrair_proprietarios(texto_normalizado)
        averbacoes = MatriculaAnalysisService._extrair_averbacoes(texto_normalizado)
        registros = MatriculaAnalysisService._extrair_registros(texto_normalizado)
        onus = MatriculaAnalysisService._extrair_onus(texto_normalizado)
        riscos = MatriculaAnalysisService._extrair_riscos(texto_normalizado)

        # =========================================================
        # 🔥 NOVO — HISTÓRICO OCR
        # =========================================================
        historico = MatriculaAnalysisService._extrair_historico_ocr(dados_ocr)

        # =========================================================
        # 🔥 NOVO — CADEIA REGISTRAL
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

            # 🔥 NOVO
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

    # =========================================================
    # PROPRIETÁRIOS
    # =========================================================
    @staticmethod
    def _extrair_proprietarios(texto: str) -> List[Dict[str, Any]]:
        proprietarios = []

        linhas = texto.split(".")
        for linha in linhas:
            if "propriet" in linha:
                nome = linha.strip()

                cpf = re.search(MatriculaAnalysisService.REGEX_CPF, linha)
                cnpj = re.search(MatriculaAnalysisService.REGEX_CNPJ, linha)

                proprietarios.append(
                    {
                        "nome": nome[:150],
                        "cpf": cpf.group(0) if cpf else None,
                        "cnpj": cnpj.group(0) if cnpj else None,
                        "tipo": "pj" if cnpj else "pf",
                    }
                )

        return proprietarios

    # =========================================================
    # AVERBAÇÕES
    # =========================================================
    @staticmethod
    def _extrair_averbacoes(texto: str) -> List[str]:
        encontrados = re.findall(MatriculaAnalysisService.REGEX_AVERBACAO, texto)

        # 🔥 normalização (remove duplicados mantendo ordem)
        vistos = set()
        resultado = []
        for item in encontrados:
            if item not in vistos:
                vistos.add(item)
                resultado.append(item)

        return resultado

    # =========================================================
    # REGISTROS
    # =========================================================
    @staticmethod
    def _extrair_registros(texto: str) -> List[str]:
        encontrados = re.findall(MatriculaAnalysisService.REGEX_REGISTRO, texto)

        # 🔥 normalização (remove duplicados mantendo ordem)
        vistos = set()
        resultado = []
        for item in encontrados:
            if item not in vistos:
                vistos.add(item)
                resultado.append(item)

        return resultado

    # =========================================================
    # ÔNUS
    # =========================================================
    @staticmethod
    def _extrair_onus(texto: str) -> List[str]:
        encontrados = []

        for palavra in MatriculaAnalysisService.PALAVRAS_ONUS:
            if palavra in texto:
                encontrados.append(palavra)

        return encontrados

    # =========================================================
    # RISCOS
    # =========================================================
    @staticmethod
    def _extrair_riscos(texto: str) -> List[str]:
        encontrados = []

        for palavra in MatriculaAnalysisService.PALAVRAS_RISCO:
            if palavra in texto:
                encontrados.append(palavra)

        return encontrados

    # =========================================================
    # CLASSIFICAÇÃO (EVOLUÍDA)
    # =========================================================
    @staticmethod
    def _classificar_matricula(
        proprietarios: List[Any],
        onus: List[str],
        riscos: List[str],
        cadeia: Dict[str, Any],
    ) -> Dict[str, Any]:

        status = "regular"

        # =========================================================
        # PRIORIDADE DE CLASSIFICAÇÃO (ordem importa)
        # =========================================================

        if not proprietarios:
            status = "irregular"

        if cadeia and not cadeia.get("cadeia_valida"):
            status = "cadeia_irregular"

        if riscos:
            status = "risco"

        if onus:
            status = "com_onus"

        # =========================================================
        # FLAGS COMPLEMENTARES
        # =========================================================
        return {
            "status": status,
            "tem_onus": bool(onus),
            "tem_risco": bool(riscos),
            "cadeia_valida": cadeia.get("cadeia_valida") if cadeia else None,
            "total_atos": cadeia.get("total_atos") if cadeia else 0,
            "proprietarios_identificados": bool(proprietarios),
        }

    # =========================================================
    # SCORE (EVOLUÍDO)
    # =========================================================
    @staticmethod
    def _calcular_score(
        proprietarios: List[Any],
        onus: List[str],
        riscos: List[str],
        cadeia: Dict[str, Any],
    ) -> int:

        score = 100

        # =========================================================
        # PROPRIETÁRIOS (CRÍTICO)
        # =========================================================
        if not proprietarios:
            score -= 30
        elif len(proprietarios) == 1:
            score -= 5  # baixa diversidade pode indicar incompleto

        # =========================================================
        # ÔNUS
        # =========================================================
        if onus:
            score -= 20

        # =========================================================
        # RISCOS
        # =========================================================
        if riscos:
            score -= 30

        # =========================================================
        # 🔥 CADEIA REGISTRAL (NOVO - CRÍTICO)
        # =========================================================
        if not cadeia.get("cadeia_valida"):
            score -= 15

        total_atos = cadeia.get("total_atos", 0)

        if total_atos == 0:
            score -= 15
        elif total_atos < 2:
            score -= 10
        elif total_atos < 4:
            score -= 5

        # =========================================================
        # NORMALIZA
        # =========================================================
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
            "cadeia_registral": {},
            "classificacao": {},
            "score_juridico": 0,
        }