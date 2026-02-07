from sqlalchemy.orm import Session

from app.models.proposal import Proposal
from app.schemas.calculation import ProposalRequest


def save_proposal(
    db: Session,
    project_id: int,
    payload: ProposalRequest,
    generated: dict,
) -> Proposal:
    """
    Persiste a proposta gerada no banco de dados.

    - project_id vem da rota
    - payload é o corpo validado (ProposalRequest)
    - generated é o retorno do generate_full_proposal()
    """

    dados = generated.get("dados")
    if not isinstance(dados, dict):
        raise ValueError("Dados de cálculo ausentes para salvar a proposta.")

    # area: vem do payload (fonte confiável)
    area = float(payload.area_hectares)

    valor_base = float(dados.get("valor_base") or 0.0)
    valor_art = float(dados.get("valor_art") or 0.0)
    extras = float(dados.get("extras") or 0.0)
    total = float(dados.get("total") or 0.0)

    html_proposta = generated.get("html_proposta") or ""
    html_contrato = generated.get("html_contrato") or ""

    pdf_path = generated.get("pdf_proposta")
    contract_pdf_path = generated.get("pdf_contrato")

    proposal = Proposal(
        project_id=project_id,
        area=area,
        valor_base=valor_base,
        valor_art=valor_art,
        extras=extras,
        total=total,
        html_proposta=html_proposta,
        html_contrato=html_contrato,
        pdf_path=pdf_path,
        contract_pdf_path=contract_pdf_path,
    )

    db.add(proposal)
    db.commit()
    db.refresh(proposal)
    return proposal


def list_proposals(db: Session, project_id: int):
    return (
        db.query(Proposal)
        .filter(Proposal.project_id == project_id)
        .order_by(Proposal.created_at.desc())
        .all()
    )
