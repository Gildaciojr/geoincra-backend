from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
import mercadopago
import os
from datetime import datetime

from app.core.deps import get_db
from app.models.pagamento import Pagamento
from app.services.pagamento_service import PagamentoService
from app.services.project_automacao_service import ProjectAutomacaoService

router = APIRouter(prefix="/pagamentos", tags=["Webhook"])


@router.post("/webhook")
async def mercadopago_webhook(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Webhook Mercado Pago
    Eventos tratados:
    - payment.created
    - payment.updated

    Fluxo:
    1. Busca pagamento no MP
    2. Localiza pagamento interno
    3. Marca parcelas como pagas (idempotente)
    4. Atualiza status do pagamento
    5. Atualiza status do projeto
    """

    payload = await request.json()

    event_type = payload.get("type")
    data_id = payload.get("data", {}).get("id")

    if event_type not in ("payment.created", "payment.updated"):
        return {"ignored": True}

    access_token = os.getenv("MERCADOPAGO_ACCESS_TOKEN")
    if not access_token:
        return {"error": "Token Mercado Pago não configurado"}

    sdk = mercadopago.SDK(access_token)

    payment_info = sdk.payment().get(data_id)
    if payment_info.get("status") != 200:
        return {"error": "Pagamento não localizado no Mercado Pago"}

    payment_data = payment_info["response"]

    status_mp = payment_data.get("status")
    external_reference = payment_data.get("external_reference")

    if not external_reference:
        return {"error": "external_reference ausente"}

    # 🔒 external_reference = pagamento.id
    try:
        pagamento_id = int(external_reference)
    except ValueError:
        return {"error": "external_reference inválido"}

    pagamento = (
        db.query(Pagamento)
        .filter(Pagamento.id == pagamento_id)
        .first()
    )

    if not pagamento:
        return {"error": "Pagamento interno não encontrado"}

    # =====================================================
    # STATUS MERCADO PAGO → SISTEMA
    # =====================================================
    if status_mp == "approved":

        # 🔒 Idempotência: só paga o que ainda não foi pago
        for parcela in pagamento.parcelas:
            if parcela.status != PagamentoService.PARCELA_PAGA:
                PagamentoService.marcar_parcela_paga(
                    db=db,
                    parcela_id=parcela.id,
                    forma_pagamento="MERCADO_PAGO",
                    observacoes="Pagamento confirmado via webhook",
                    pago_em=datetime.utcnow(),
                )

        # 🔄 Atualiza status do projeto
        ProjectAutomacaoService.aplicar_status_automatico(
            db,
            pagamento.project_id,
        )

    return {"status": "ok"}
