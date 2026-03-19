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
    def analisar(texto: Optional[str]) -> Dict[str, Any]:
        if not texto or not isinstance(texto, str):
            return MatriculaAnalysisService._retorno_vazio("Texto da matrícula ausente")

        texto_normalizado = MatriculaAnalysisService._normalizar_texto(texto)

        proprietarios = MatriculaAnalysisService._extrair_proprietarios(texto_normalizado)
        averbacoes = MatriculaAnalysisService._extrair_averbacoes(texto_normalizado)
        registros = MatriculaAnalysisService._extrair_registros(texto_normalizado)
        onus = MatriculaAnalysisService._extrair_onus(texto_normalizado)
        riscos = MatriculaAnalysisService._extrair_riscos(texto_normalizado)

        classificacao = MatriculaAnalysisService._classificar_matricula(
            proprietarios=proprietarios,
            onus=onus,
            riscos=riscos,
        )

        score = MatriculaAnalysisService._calcular_score(
            proprietarios=proprietarios,
            onus=onus,
            riscos=riscos,
        )

        return {
            "success": True,
            "proprietarios": proprietarios,
            "averbacoes": averbacoes,
            "registros": registros,
            "onus": onus,
            "riscos": riscos,
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
        return re.findall(MatriculaAnalysisService.REGEX_AVERBACAO, texto)

    # =========================================================
    # REGISTROS
    # =========================================================
    @staticmethod
    def _extrair_registros(texto: str) -> List[str]:
        return re.findall(MatriculaAnalysisService.REGEX_REGISTRO, texto)

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
    # CLASSIFICAÇÃO
    # =========================================================
    @staticmethod
    def _classificar_matricula(
        proprietarios: List[Any],
        onus: List[str],
        riscos: List[str],
    ) -> Dict[str, Any]:
        status = "regular"

        if not proprietarios:
            status = "irregular"

        if riscos:
            status = "risco"

        if onus:
            status = "com_onus"

        return {
            "status": status,
            "tem_onus": bool(onus),
            "tem_risco": bool(riscos),
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
    ) -> int:
        score = 100

        if not proprietarios:
            score -= 30

        if onus:
            score -= 20

        if riscos:
            score -= 30

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
            "classificacao": {},
            "score_juridico": 0,
        }