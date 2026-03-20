from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.project_status import ProjectStatus
from app.schemas.project_status import ProjectStatusCreate

from app.models.pagamento import Pagamento
from app.services.pagamento_automacao_service import PagamentoAutomacaoService


def definir_status_projeto(
    db: Session,
    project_id: int,
    data: ProjectStatusCreate,
) -> ProjectStatus:

    project = db.query(Project).get(project_id)
    if not project:
        raise ValueError("Projeto não encontrado.")

    atual = (
        db.query(ProjectStatus)
        .filter(
            ProjectStatus.project_id == project_id,
            ProjectStatus.ativo.is_(True),
        )
        .first()
    )

    if atual and (atual.status or "").upper() == (data.status or "").upper():
        project.status = data.status
        db.commit()
        db.refresh(atual)
        return atual

    db.query(ProjectStatus).filter(
        ProjectStatus.project_id == project_id,
        ProjectStatus.ativo.is_(True),
    ).update({"ativo": False})

    status = ProjectStatus(
        project_id=project_id,
        status=data.status,
        descricao=data.descricao,
        ativo=True,
        definido_automaticamente=data.definido_automaticamente,
        definido_por_usuario_id=data.definido_por_usuario_id,
    )

    db.add(status)
    project.status = data.status

    db.commit()
    db.refresh(status)

    # 🔥 ISOLADO E SEGURO
    try:
        pagamentos = (
            db.query(Pagamento)
            .filter(Pagamento.project_id == project_id)
            .all()
        )

        for pagamento in pagamentos:
            PagamentoAutomacaoService.avaliar_liberacao_pagamento(db, pagamento)

        db.commit()

    except Exception as e:
        db.rollback()
        print(f"⚠️ Falha ao atualizar pagamentos após status: {str(e)}")

    return status