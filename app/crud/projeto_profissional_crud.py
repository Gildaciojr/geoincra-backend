from datetime import datetime
from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.profissional import Profissional
from app.models.projeto_profissional import ProjetoProfissional
from app.schemas.projeto_profissional import (
    ProjetoProfissionalCreate,
    ProjetoProfissionalUpdate,
)


def vincular_profissional_ao_projeto(
    db: Session,
    project_id: int,
    data: ProjetoProfissionalCreate,
) -> ProjetoProfissional:
    project = db.query(Project).get(project_id)
    if not project:
        raise ValueError("Projeto não encontrado.")

    profissional = db.query(Profissional).get(data.profissional_id)
    if not profissional:
        raise ValueError("Profissional não encontrado.")

    # 🔒 Desativa vínculo anterior ativo
    db.query(ProjetoProfissional).filter(
        ProjetoProfissional.project_id == project_id,
        ProjetoProfissional.ativo.is_(True),
    ).update({"ativo": False})

    vinculo = ProjetoProfissional(
        project_id=project_id,
        profissional_id=data.profissional_id,
        proposta_profissional_id=data.proposta_profissional_id,
        status_execucao="ACEITO",
        ativo=True,
    )

    db.add(vinculo)
    db.commit()
    db.refresh(vinculo)
    return vinculo


def obter_profissional_ativo(
    db: Session,
    project_id: int,
) -> ProjetoProfissional | None:
    return (
        db.query(ProjetoProfissional)
        .filter(
            ProjetoProfissional.project_id == project_id,
            ProjetoProfissional.ativo.is_(True),
        )
        .first()
    )


def atualizar_status_execucao(
    db: Session,
    vinculo_id: int,
    data: ProjetoProfissionalUpdate,
) -> ProjetoProfissional | None:
    vinculo = db.query(ProjetoProfissional).get(vinculo_id)
    if not vinculo:
        return None

    payload = data.model_dump(exclude_unset=True)

    for field, value in payload.items():
        setattr(vinculo, field, value)

    if payload.get("status_execucao") == "FINALIZADO":
        vinculo.finalizado_em = datetime.utcnow()
        vinculo.ativo = False

    db.commit()
    db.refresh(vinculo)
    return vinculo
