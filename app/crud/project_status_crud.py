# app/crud/project_status_crud.py

from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.project_status import ProjectStatus
from app.schemas.project_status import ProjectStatusCreate

from app.models.pagamento import Pagamento
from app.services.pagamento_automacao_service import PagamentoAutomacaoService


# =========================================================
# DEFINIR STATUS
# =========================================================
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

    # Evita recriar o mesmo status
    if atual and (atual.status or "").upper() == (data.status or "").upper():
        project.status = data.status
        db.commit()
        db.refresh(atual)
        return atual

    # Desativa status atual
    db.query(ProjectStatus).filter(
        ProjectStatus.project_id == project_id,
        ProjectStatus.ativo.is_(True),
    ).update({"ativo": False})

    # Cria novo status
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

    # =========================================================
    # AUTOMAÇÃO FINANCEIRA (ISOLADA)
    # =========================================================
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


# =========================================================
# STATUS ATUAL
# =========================================================
def obter_status_atual(
    db: Session,
    project_id: int,
) -> ProjectStatus | None:
    """
    Retorna o status ativo atual do projeto.
    """

    return (
        db.query(ProjectStatus)
        .filter(
            ProjectStatus.project_id == project_id,
            ProjectStatus.ativo.is_(True),
        )
        .order_by(ProjectStatus.id.desc())
        .first()
    )


# =========================================================
# HISTÓRICO DE STATUS
# =========================================================
def listar_historico_status(
    db: Session,
    project_id: int,
) -> list[ProjectStatus]:
    """
    Retorna todos os status do projeto (histórico completo).
    """

    return (
        db.query(ProjectStatus)
        .filter(ProjectStatus.project_id == project_id)
        .order_by(ProjectStatus.id.desc())
        .all()
    )