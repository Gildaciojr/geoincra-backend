# app/crud/profissional_selecao_crud.py

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.profissional_selecao import ProfissionalSelecao


def get_selecao_atual(db: Session, project_id: int) -> ProfissionalSelecao | None:
    return (
        db.query(ProfissionalSelecao)
        .filter(
            ProfissionalSelecao.project_id == project_id,
            ProfissionalSelecao.is_atual.is_(True),
        )
        .order_by(ProfissionalSelecao.created_at.desc())
        .first()
    )


def list_historico_selecoes(db: Session, project_id: int) -> list[ProfissionalSelecao]:
    return (
        db.query(ProfissionalSelecao)
        .filter(ProfissionalSelecao.project_id == project_id)
        .order_by(ProfissionalSelecao.created_at.desc())
        .all()
    )
