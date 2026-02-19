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

# ACEITE + PAGAMENTO
from app.services.proposal_acceptance_service import ProposalAcceptanceService

router = APIRouter(prefix="/propostas", tags=["Propostas"])


# ============================================================
# 🔒 HELPERS
# ============================================================
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


# ============================================================
# 🔒 GERAR PROPOSTA + CONTRATO (PDF)
# POST /api/propostas/generate/{project_id}
# ============================================================
@router.post("/generate/{project_id}")
def generate_proposal(
    project_id: int,
    payload: ProposalRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    _check_project_owner(db, project_id, current_user.id)

    # 1️⃣ GERA PROPOSTA (CÁLCULO + PDFs)
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
            detail="Falha ao gerar proposta/contrato.",
        )

    # 2️⃣ SALVA PROPOSTA NO BANCO
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

    # 3️⃣ ATUALIZA STATUS AUTOMÁTICO DO PROJETO
    from app.services.project_automacao_service import ProjectAutomacaoService
    ProjectAutomacaoService.aplicar_status_automatico(db, project_id)

    proposta_filename = Path(saved.pdf_path).name if saved.pdf_path else None
    contrato_filename = Path(saved.contract_pdf_path).name if saved.contract_pdf_path else None

    pdf_url = (
        f"/api/files/pdf?path=propostas/project_{project_id}/{proposta_filename}"
        if proposta_filename
        else None
    )
    contract_url = (
        f"/api/files/pdf?path=propostas/project_{project_id}/{contrato_filename}"
        if contrato_filename
        else None
    )

    return {
        "mensagem": "Proposta gerada com sucesso",
        "proposta_id": saved.id,
        "valor_base": generated["dados"]["valor_base"],
        "extras": generated["dados"]["extras"],
        "total": generated["dados"]["total"],
        "pdf_url": pdf_url,
        "contract_url": contract_url,
    }


# ============================================================
# 🔒 ACEITAR PROPOSTA (LIBERA PAGAMENTO)
# POST /api/propostas/accept/{proposal_id}
# ============================================================
@router.post("/accept/{proposal_id}")
def accept_proposal(
    proposal_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    try:
        pagamento = ProposalAcceptanceService.accept_proposal(
            db=db,
            proposal_id=proposal_id,
            user_id=current_user.id,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Erro ao aceitar proposta.",
        )

    return {
        "mensagem": "Proposta aceita com sucesso. Pagamento liberado.",
        "pagamento_id": pagamento.id,
        "status_pagamento": pagamento.status,
    }


# ============================================================
# 🔒 HISTÓRICO DE PROPOSTAS (ESTÁVEL)
# GET /api/propostas/history/{project_id}
# ============================================================
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

    proposals = list_proposals(db, project_id)

    resultado: list[ProposalOut] = []

    for p in proposals:
        resultado.append(
            ProposalOut(
                id=p.id,
                project_id=p.project_id,
                area=p.area,
                valor_base=p.valor_base,
                valor_art=p.valor_art,
                extras=p.extras,
                total=p.total,
                pdf_path=p.pdf_path,
                contract_pdf_path=p.contract_pdf_path,
                created_at=p.created_at,
            )
        )

    return resultado
