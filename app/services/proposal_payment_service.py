from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.pagamento import Pagamento
from app.models.proposal import Proposal


def criar_pagamento_para_proposta(
    db: Session,
    proposal: Proposal,
) -> Pagamento:
    """
    Cria um pagamento automático vinculado à proposta.

    As parcelas serão geradas posteriormente pelo PagamentoService,
    respeitando o modelo configurado (100, 50_50, 20_30_50 etc).
    """

    pagamento = Pagamento(
        project_id=proposal.project_id,
        descricao=f"Pagamento referente à proposta #{proposal.id}",
        valor=float(proposal.total),
        total=float(proposal.total),
        tipo="ENTRADA",
        status="PENDENTE",
        modelo="100",  # compatível com PagamentoService.MODELOS_PADRAO
        data_vencimento=datetime.utcnow() + timedelta(days=7),
        bloqueia_fluxo=True,
        criado_automaticamente=True,
    )

    db.add(pagamento)
    db.commit()
    db.refresh(pagamento)

    return pagamento
