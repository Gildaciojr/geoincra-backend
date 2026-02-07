from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user_required
from app.models.user import User
from app.models.project import Project
from app.schemas.calculation import ProposalRequest
from app.schemas.proposal_out import ProposalOut
from app.services.proposal_service import generate_full_proposal
from app.services.proposal_history_service import save_proposal, list_proposals

router = APIRouter(prefix="/propostas", tags=["Propostas"])


def _check_project_owner(db: Session, project_id: int, user_id: int):
    project = (
        db.query(Project)
        .filter(
            Project.id == project_id,
            Project.owner_id == user_id,
        )
        .first()
    )

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Projeto não encontrado ou não pertence ao usuário",
        )

    return project


@router.post("/generate/{project_id}")
def generate_proposal(
    project_id: int,
    payload: ProposalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    _check_project_owner(db, project_id, current_user.id)

    try:
        generated = generate_full_proposal(
            db=db,
            payload=payload,
            project_id=project_id,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Falha ao gerar proposta/contrato. Verifique os logs.",
        )

    try:
        saved = save_proposal(
            db=db,
            project_id=project_id,
            payload=payload,
            generated=generated,
        )
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Falha ao salvar a proposta.",
        )

    proposta_filename = Path(saved.pdf_path).name if saved.pdf_path else None
    contrato_filename = (
        Path(saved.contract_pdf_path).name if saved.contract_pdf_path else None
    )

    return {
        "mensagem": "Proposta gerada com sucesso",
        "proposta_id": saved.id,
        "valor_base": generated["dados"]["valor_base"],
        "extras": generated["dados"]["extras"],
        "total": generated["dados"]["total"],
        "pdf_path": (
            f"/files/pdf?path=propostas/{proposta_filename}"
            if proposta_filename
            else None
        ),
        "contract_pdf_path": (
            f"/files/pdf?path=propostas/{contrato_filename}"
            if contrato_filename
            else None
        ),
    }


@router.get(
    "/history/{project_id}",
    response_model=list[ProposalOut],
)
def list_history(
    project_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    _check_project_owner(db, project_id, current_user.id)
    return list_proposals(db, project_id)
