from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user_required
from app.models.user import User
from app.models.pagamento import Pagamento
from app.services.mercadopago_service import MercadoPagoService

router = APIRouter(prefix="/pagamentos", tags=["Pagamentos"])


@router.post("/{pagamento_id}/checkout")
def criar_checkout(
    pagamento_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_required),
):
    pagamento = db.query(Pagamento).filter(Pagamento.id == pagamento_id).first()

    if not pagamento:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")

    if pagamento.status == "PAGO":
        raise HTTPException(status_code=400, detail="Pagamento já quitado")

    try:
        checkout = MercadoPagoService.criar_checkout_pro(db, pagamento)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    return {
        "checkout_url": checkout["init_point"],
        "sandbox_url": checkout.get("sandbox_init_point"),
        "preference_id": checkout["id"],
    }
