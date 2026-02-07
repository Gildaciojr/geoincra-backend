from __future__ import annotations
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.project_automacao import (
    AutomacaoStatusDiagnostico,
    AutomacaoAplicarResponse,
    AutomacaoMotivo,
)
from app.services.project_automacao_service import ProjectAutomacaoService
from app.crud.project_crud import get_project

router = APIRouter(prefix="/projects", tags=["Automação Projetos"])


@router.get("/{project_id}/automacao/diagnostico", response_model=AutomacaoStatusDiagnostico)
def diagnosticar_status_projeto(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project(db, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    status_sugerido, desc, bloqueado, bloqueio_motivo, motivos = (
        ProjectAutomacaoService.diagnosticar_status(db, project_id)
    )

    now = datetime.now(timezone.utc)
    return AutomacaoStatusDiagnostico(
        project_id=project_id,
        status_sugerido=status_sugerido,
        descricao_status=desc,
        bloqueado=bloqueado,
        bloqueio_motivo=bloqueio_motivo,
        gerado_em=now,
        motivos=[AutomacaoMotivo(codigo=m.codigo, descricao=m.descricao) for m in motivos],
    )


@router.post("/{project_id}/automacao/aplicar", response_model=AutomacaoAplicarResponse)
def aplicar_status_automatico(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project(db, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    status_aplicado, criado_novo, motivos = (
        ProjectAutomacaoService.aplicar_status_automatico(db, project_id)
    )

    now = datetime.now(timezone.utc)
    return AutomacaoAplicarResponse(
        project_id=project_id,
        status_aplicado=status_aplicado,
        criado_novo_status=criado_novo,
        gerado_em=now,
        motivos=[AutomacaoMotivo(codigo=m.codigo, descricao=m.descricao) for m in motivos],
    )
