from __future__ import annotations

from typing import Optional

from app.models.profissional import Profissional
from app.models.project import Project


class ProfissionalScoreService:
    """
    Serviço responsável por calcular o SCORE TÉCNICO
    de um profissional para um projeto específico.

    NÃO escolhe
    NÃO persiste
    NÃO altera status

    Apenas calcula pontuação objetiva.
    """

    PESO_AVALIACAO = 4.0
    PESO_EXPERIENCIA = 3.0
    PESO_ESPECIALIDADE = 2.0
    PESO_DISPONIBILIDADE = 1.0

    @staticmethod
    def calcular_score(
        profissional: Profissional,
        project: Optional[Project] = None,
    ) -> float:
        """
        Retorna score final normalizado.
        """

        if not profissional.ativo:
            return 0.0

        score = 0.0

        # =========================================================
        # 1️⃣ Avaliação média
        # =========================================================
        if profissional.rating_medio:
            score += (
                profissional.rating_medio
                * ProfissionalScoreService.PESO_AVALIACAO
            )

        # =========================================================
        # 2️⃣ Experiência (quantidade de serviços/projetos)
        # Normalização simples (cada 5 = +1 ponto base)
        # =========================================================
        score += (
            (profissional.total_servicos / 5)
            * ProfissionalScoreService.PESO_EXPERIENCIA
        )

        # =========================================================
        # 3️⃣ Especialidade compatível com o projeto
        # =========================================================
        if project and profissional.especialidades and project.tipo_processo:
            if project.tipo_processo.lower() in profissional.especialidades.lower():
                score += ProfissionalScoreService.PESO_ESPECIALIDADE

        # =========================================================
        # 4️⃣ Disponibilidade base
        # =========================================================
        score += ProfissionalScoreService.PESO_DISPONIBILIDADE

        return round(score, 2)