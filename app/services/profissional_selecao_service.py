# app/services/profissional_selecao_service.py

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.profissional import Profissional
from app.models.profissional_selecao import ProfissionalSelecao
from app.services.profissional_score_service import ProfissionalScoreService


class ProfissionalSelecaoService:
    """
    Serviço responsável por:
    - ranquear profissionais elegíveis
    - escolher o melhor (score)
    - registrar decisão (auditoria)
    - manter histórico

    NÃO usa APIs externas.
    """

    @staticmethod
    def _buscar_projeto(db: Session, project_id: int) -> Project:
        project = db.query(Project).filter(Project.id == project_id).first()
        if not project:
            raise HTTPException(status_code=404, detail="Projeto não encontrado.")
        return project

    @staticmethod
    def _buscar_profissionais_ativos(db: Session) -> List[Profissional]:
        return (
            db.query(Profissional)
            .filter(Profissional.ativo.is_(True))
            .order_by(Profissional.nome_completo.asc())
            .all()
        )

    @staticmethod
    def _rankear(
        project: Project,
        profissionais: List[Profissional],
    ) -> List[Tuple[Profissional, float]]:
        ranqueados: List[Tuple[Profissional, float]] = []
        for p in profissionais:
            score = ProfissionalScoreService.calcular_score(profissional=p, project=project)
            ranqueados.append((p, score))

        ranqueados.sort(key=lambda x: x[1], reverse=True)
        return ranqueados

    @staticmethod
    def selecionar_melhor_profissional(
        db: Session,
        project_id: int,
        automatico: bool = True,
        escolhido_por_user_id: Optional[int] = None,
        observacao: Optional[str] = None,
    ) -> ProfissionalSelecao:
        """
        Seleciona automaticamente o melhor profissional (por score)
        e registra a seleção como "atual", desativando a anterior.
        """

        project = ProfissionalSelecaoService._buscar_projeto(db, project_id)
        profissionais = ProfissionalSelecaoService._buscar_profissionais_ativos(db)

        if not profissionais:
            raise HTTPException(status_code=400, detail="Nenhum profissional ativo disponível.")

        ranqueados = ProfissionalSelecaoService._rankear(project, profissionais)

        # Lista do primeiro em diante
        melhor_prof, melhor_score = ranqueados[0]

        criterios: Dict[str, object] = {
            "project_id": project.id,
            "tipo_processo": project.tipo_processo,
            "automatico": automatico,
            "observacao": observacao,
            "ranqueamento": [
                {
                    "profissional_id": p.id,
                    "nome": p.nome_completo,
                    "score": s,
                    "avaliacao_media": p.avaliacao_media,
                    "total_projetos": p.total_projetos,
                    "especialidades": p.especialidades,
                    "ativo": p.ativo,
                }
                for (p, s) in ranqueados
            ],
            "escolhido": {
                "profissional_id": melhor_prof.id,
                "nome": melhor_prof.nome_completo,
                "score": melhor_score,
            },
            "gerado_em": datetime.utcnow().isoformat(),
        }

        # Desativador de seleção atual 
        db.query(ProfissionalSelecao).filter(
            ProfissionalSelecao.project_id == project_id,
            ProfissionalSelecao.is_atual.is_(True),
        ).update({"is_atual": False})

        selecao = ProfissionalSelecao(
            project_id=project_id,
            profissional_id=melhor_prof.id,
            score=float(melhor_score),
            criterios_json=criterios,
            automatico=automatico,
            escolhido_por_user_id=escolhido_por_user_id,
            observacoes=observacao,
            escolhido_em=datetime.utcnow(),
            is_atual=True,
        )

        db.add(selecao)
        db.commit()
        db.refresh(selecao)

        return selecao

    @staticmethod
    def selecionar_profissional_manual(
        db: Session,
        project_id: int,
        profissional_id: int,
        escolhido_por_user_id: Optional[int] = None,
        observacao: Optional[str] = None,
    ) -> ProfissionalSelecao:
        """
        Seleção manual (sem APIs).
        Mantém auditoria e histórico, com is_atual=True.
        """

        project = ProfissionalSelecaoService._buscar_projeto(db, project_id)

        prof = db.query(Profissional).filter(Profissional.id == profissional_id).first()
        if not prof:
            raise HTTPException(status_code=404, detail="Profissional não encontrado.")
        if not prof.ativo:
            raise HTTPException(status_code=400, detail="Profissional está desativado.")

        score = ProfissionalScoreService.calcular_score(profissional=prof, project=project)

        criterios: Dict[str, object] = {
            "project_id": project.id,
            "tipo_processo": project.tipo_processo,
            "automatico": False,
            "observacao": observacao,
            "escolhido": {
                "profissional_id": prof.id,
                "nome": prof.nome_completo,
                "score": float(score),
            },
            "gerado_em": datetime.utcnow().isoformat(),
        }

        db.query(ProfissionalSelecao).filter(
            ProfissionalSelecao.project_id == project_id,
            ProfissionalSelecao.is_atual.is_(True),
        ).update({"is_atual": False})

        selecao = ProfissionalSelecao(
            project_id=project_id,
            profissional_id=prof.id,
            score=float(score),
            criterios_json=criterios,
            automatico=False,
            escolhido_por_user_id=escolhido_por_user_id,
            observacoes=observacao,
            escolhido_em=datetime.utcnow(),
            is_atual=True,
        )

        db.add(selecao)
        db.commit()
        db.refresh(selecao)

        return selecao
