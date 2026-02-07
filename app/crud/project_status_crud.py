from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.project import Project
from app.models.project_status import ProjectStatus
from app.schemas.project_status import ProjectStatusCreate

# 🔥 Automação de pagamento após mudança de status
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

    # =========================================================
    # ✅ IDempotência (SaaS-safe)
    # Se o status atual já é o mesmo que está sendo solicitado,
    # não cria novo histórico nem desativa o atual.
    # =========================================================
    atual = (
        db.query(ProjectStatus)
        .filter(
            ProjectStatus.project_id == project_id,
            ProjectStatus.ativo.is_(True),
        )
        .first()
    )

    if atual and (atual.status or "").upper() == (data.status or "").upper():
        # Mesmo status -> apenas garante snapshot no Project e retorna o status atual
        project.status = data.status
        db.commit()
        db.refresh(atual)
        return atual

    # =========================================================
    # 1️⃣ Desativa status anterior (histórico)
    # =========================================================
    db.query(ProjectStatus).filter(
        ProjectStatus.project_id == project_id,
        ProjectStatus.ativo.is_(True),
    ).update({"ativo": False})

    # =========================================================
    # 2️⃣ Cria novo status (histórico)
    # =========================================================
    status = ProjectStatus(
        project_id=project_id,
        status=data.status,
        descricao=data.descricao,
        ativo=True,
        definido_automaticamente=data.definido_automaticamente,
        definido_por_usuario_id=data.definido_por_usuario_id,
    )
    db.add(status)

    # =========================================================
    # 🔥 3️⃣ FONTE ÚNICA (snapshot no Project)
    # =========================================================
    project.status = data.status

    # =========================================================
    # 4️⃣ Commit único (atômico)
    # =========================================================
    db.commit()
    db.refresh(status)

    # =========================================================
    # ✅ 5️⃣ Evento de domínio: STATUS MUDOU -> reavaliar pagamentos
    # (liberação automática de parcelas conforme andamento técnico)
    # =========================================================
    pagamentos = (
        db.query(Pagamento)
        .filter(Pagamento.project_id == project_id)
        .all()
    )

    for pagamento in pagamentos:
        PagamentoAutomacaoService.avaliar_liberacao_pagamento(db, pagamento)

    return status


def obter_status_atual(
    db: Session,
    project_id: int,
) -> ProjectStatus | None:
    return (
        db.query(ProjectStatus)
        .filter(
            ProjectStatus.project_id == project_id,
            ProjectStatus.ativo.is_(True),
        )
        .first()
    )


def listar_historico_status(
    db: Session,
    project_id: int,
) -> list[ProjectStatus]:
    return (
        db.query(ProjectStatus)
        .filter(ProjectStatus.project_id == project_id)
        .order_by(ProjectStatus.created_at.asc())
        .all()
    )
