from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.proposal import Proposal
from app.models.pagamento import Pagamento
from app.services.pagamento_service import PagamentoService
from app.services.project_automacao_service import ProjectAutomacaoService


class ProposalAcceptanceService:

    @staticmethod
    def accept_proposal(
        db: Session,
        proposal_id: int,
        user_id: int,
    ) -> Pagamento:

        proposal = (
            db.query(Proposal)
            .filter(Proposal.id == proposal_id)
            .first()
        )

        if not proposal:
            raise ValueError("Proposta não encontrada.")

        if proposal.status != "GERADA":
            raise ValueError("Proposta já aceita ou inválida.")

        # 1️⃣ MARCA ACEITE DA PROPOSTA
        proposal.status = "ACEITA"
        proposal.accepted_at = datetime.utcnow()
        proposal.accepted_by_user_id = user_id

        db.commit()
        db.refresh(proposal)

        # 2️⃣ CRIA PAGAMENTO VINCULADO À PROPOSTA
        pagamento = Pagamento(
            project_id=proposal.project_id,
            proposal_id=proposal.id,
            descricao=f"Pagamento da proposta #{proposal.id}",
            valor=proposal.total,
            total=proposal.total,
            tipo="ENTRADA",
            status="PENDENTE",
            modelo="100",  # Checkout Pro
            data_vencimento=datetime.utcnow() + timedelta(days=2),
            bloqueia_fluxo=True,
            criado_automaticamente=True,
        )

        db.add(pagamento)
        db.commit()
        db.refresh(pagamento)

        # 3️⃣ GERA PARCELA(S)
        PagamentoService.gerar_parcelas_padrao(db, pagamento)

        # 4️⃣ STATUS EXPLÍCITO DO PROJETO
        ProjectAutomacaoService.definir_status_manual(
            db=db,
            project_id=proposal.project_id,
            status="AGUARDANDO_PAGAMENTO",
            descricao="Proposta e contrato aceitos pelo cliente.",
            user_id=user_id,
        )

        return pagamento
