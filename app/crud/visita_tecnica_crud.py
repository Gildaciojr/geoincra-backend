from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.models.visita_tecnica import VisitaTecnica
from app.models.project import Project

from app.schemas.visita_tecnica import (
    VisitaTecnicaCreate,
    VisitaTecnicaUpdate,
)

from app.crud.profissional_selecao_crud import get_selecao_atual
from app.services.timeline_service import TimelineService


# =========================================================
# CREATE
# =========================================================
def criar_visita(
    db: Session,
    project_id: int,
    data: VisitaTecnicaCreate,
) -> VisitaTecnica:

    # 🔎 valida projeto
    project = db.query(Project).get(project_id)
    if not project:
        raise ValueError("Projeto não encontrado.")

    # 🔎 valida profissional selecionado
    selecao = get_selecao_atual(db, project_id)
    if not selecao:
        raise ValueError("Nenhum profissional selecionado para este projeto.")

    profissional_id = selecao.profissional_id

    # 🔒 BLOQUEIO DE AGENDA (ANTI DUPLICIDADE)
    conflito = (
        db.query(VisitaTecnica)
        .filter(
            and_(
                VisitaTecnica.profissional_id == profissional_id,
                VisitaTecnica.data_agendada == data.data_agendada,
                VisitaTecnica.status != "CANCELADA",
            )
        )
        .first()
    )

    if conflito:
        raise ValueError("Este profissional já possui uma visita neste horário.")

    # 📌 criação
    visita = VisitaTecnica(
        project_id=project_id,
        profissional_id=profissional_id,
        data_agendada=data.data_agendada,
        observacoes=data.observacoes,
        status="PENDENTE",
    )

    db.add(visita)
    db.commit()
    db.refresh(visita)

    # 📅 TIMELINE — AGENDAMENTO
    TimelineService.registrar_evento(
        db=db,
        project_id=project_id,
        titulo="Visita técnica agendada",
        descricao=(
            f"Profissional ID {profissional_id} agendado "
            f"para {data.data_agendada.strftime('%d/%m/%Y %H:%M')}"
        ),
        status="Pendente",
    )

    return visita


# =========================================================
# LIST POR PROJETO
# =========================================================
def listar_visitas_projeto(
    db: Session,
    project_id: int,
):
    return (
        db.query(VisitaTecnica)
        .filter(VisitaTecnica.project_id == project_id)
        .order_by(VisitaTecnica.data_agendada.asc())
        .all()
    )


# =========================================================
# AGENDA DO PROFISSIONAL
# =========================================================
def agenda_profissional(
    db: Session,
    profissional_id: int,
):
    return (
        db.query(VisitaTecnica)
        .filter(VisitaTecnica.profissional_id == profissional_id)
        .order_by(VisitaTecnica.data_agendada.asc())
        .all()
    )


# =========================================================
# UPDATE
# =========================================================
def atualizar_visita(
    db: Session,
    visita_id: int,
    data: VisitaTecnicaUpdate,
):

    visita = db.query(VisitaTecnica).get(visita_id)

    if not visita:
        return None

    payload = data.model_dump(exclude_unset=True)

    # =========================================================
    # 🔒 BLOQUEIO DE CONFLITO (se alterar data)
    # =========================================================
    if "data_agendada" in payload:
        conflito = (
            db.query(VisitaTecnica)
            .filter(
                and_(
                    VisitaTecnica.profissional_id == visita.profissional_id,
                    VisitaTecnica.data_agendada == payload["data_agendada"],
                    VisitaTecnica.id != visita.id,
                    VisitaTecnica.status != "CANCELADA",
                )
            )
            .first()
        )

        if conflito:
            raise ValueError("Conflito de agenda para este profissional.")

    status_anterior = visita.status

    # aplica atualização
    for field, value in payload.items():
        setattr(visita, field, value)

    db.commit()
    db.refresh(visita)

    # =========================================================
    # 📅 TIMELINE — MUDANÇAS DE STATUS
    # =========================================================
    if "status" in payload and payload["status"] != status_anterior:

        if payload["status"] == "REALIZADA":
            TimelineService.registrar_evento(
                db=db,
                project_id=visita.project_id,
                titulo="Visita técnica realizada",
                descricao=f"Visita ID {visita.id} concluída com sucesso.",
                status="Concluído",
            )

        elif payload["status"] == "CANCELADA":
            TimelineService.registrar_evento(
                db=db,
                project_id=visita.project_id,
                titulo="Visita técnica cancelada",
                descricao=f"Visita ID {visita.id} foi cancelada.",
                status="Concluído",
            )

        elif payload["status"] == "CONFIRMADA":
            TimelineService.registrar_evento(
                db=db,
                project_id=visita.project_id,
                titulo="Visita técnica confirmada",
                descricao=f"Visita ID {visita.id} confirmada.",
                status="Em Andamento",
            )

    return visita