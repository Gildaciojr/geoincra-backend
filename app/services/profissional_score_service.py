# app/services/profissional_score_service.py

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

    # Pesos
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
        if profissional.avaliacao_media:
            score += profissional.avaliacao_media * ProfissionalScoreService.PESO_AVALIACAO

        # =========================================================
        # 2️⃣ Experiência (quantidade de projetos)
        # Normalização simples (cada 5 projetos = +1 ponto)
        # =========================================================
        score += (profissional.total_projetos / 5) * ProfissionalScoreService.PESO_EXPERIENCIA

        # =========================================================
        # 3️⃣ Especialidade compatível
        # =========================================================
        if project and profissional.especialidades:
            if project.tipo_processo:
                if project.tipo_processo.lower() in profissional.especialidades.lower():
                    score += ProfissionalScoreService.PESO_ESPECIALIDADE

        # =========================================================
        # 4️⃣ Disponibilidade
        # =========================================================
        score += ProfissionalScoreService.PESO_DISPONIBILIDADE

        return round(score, 2)
