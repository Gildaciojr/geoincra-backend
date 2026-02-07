from __future__ import annotations
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user
from app.models.user import User
from app.schemas.project_marcos import (
    MarcoAvaliacaoResponse,
    MarcoAplicarResponse,
    MarcoMotivo,
)
from app.services.project_marcos_service import ProjectMarcosService
from app.crud.project_crud import get_project

router = APIRouter()


@router.get(
    "/projects/{project_id}/marcos/avaliar-sigef",
    response_model=MarcoAvaliacaoResponse,
)
def avaliar_marco_sigef(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project(db, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    pode, status_atual, status_sugerido, desc, motivos = (
        ProjectMarcosService.avaliar_avanco_para_sigef(db, project_id)
    )

    now = datetime.now(timezone.utc)
    return MarcoAvaliacaoResponse(
        project_id=project_id,
        pode_avancar=pode,
        status_atual=status_atual,
        status_sugerido=status_sugerido,
        descricao=desc,
        gerado_em=now,
        motivos=[MarcoMotivo(codigo=m.codigo, descricao=m.descricao) for m in motivos],
    )


@router.post(
    "/projects/{project_id}/marcos/aplicar-sigef",
    response_model=MarcoAplicarResponse,
)
def aplicar_marco_sigef(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project(db, project_id)
    if not project or project.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Projeto não encontrado")

    aplicado, status_aplicado, motivos = (
        ProjectMarcosService.aplicar_avanco_para_sigef(db, project_id)
    )

    now = datetime.now(timezone.utc)
    return MarcoAplicarResponse(
        project_id=project_id,
        aplicado=aplicado,
        status_aplicado=status_aplicado,
        gerado_em=now,
        motivos=[MarcoMotivo(codigo=m.codigo, descricao=m.descricao) for m in motivos],
    )
