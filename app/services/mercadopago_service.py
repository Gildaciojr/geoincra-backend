import os
import mercadopago
from sqlalchemy.orm import Session

from app.models.pagamento import Pagamento


class MercadoPagoService:

    @staticmethod
    def criar_checkout_pro(db: Session, pagamento: Pagamento) -> dict:
        """
        Cria uma preferência de pagamento no Mercado Pago (Checkout Pro)
        """

        access_token = os.getenv("MERCADO_PAGO_ACCESS_TOKEN")
        if not access_token:
            raise ValueError("MERCADO_PAGO_ACCESS_TOKEN não configurado")

        sdk = mercadopago.SDK(access_token)

        preference_data = {
            "items": [
                {
                    "id": f"pagamento_{pagamento.id}",
                    "title": pagamento.descricao,
                    "quantity": 1,
                    "currency_id": "BRL",
                    "unit_price": float(pagamento.total),
                }
            ],
            "external_reference": str(pagamento.id),
            "notification_url": "https://api.geoincra.escriturafacil.com/api/pagamentos/webhook",
            "auto_return": "approved",
            "back_urls": {
                "success": "https://geoincra.escriturafacil.com/pagamento/sucesso",
                "failure": "https://geoincra.escriturafacil.com/pagamento/erro",
                "pending": "https://geoincra.escriturafacil.com/pagamento/pendente",
            },
        }

        preference_response = sdk.preference().create(preference_data)

        if preference_response["status"] != 201:
            raise ValueError("Erro ao criar Checkout Pro")

        return preference_response["response"]
