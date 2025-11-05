"""
Handler: create payment transaction
SPDX - License - Identifier: LGPL - 3.0 - or -later
Auteurs : Gabriel C. Ullmann, Fabio Petrillo, 2025
"""
import config
import requests
from logger import Logger
from handlers.handler import Handler
from order_saga_state import OrderSagaState

class CreatePaymentHandler(Handler):
    """ Handle the creation of a payment transaction for a given order. Trigger rollback of previous steps in case of failure. """

    def __init__(self, order_id, order_data):
        """ Constructor method """
        self.order_id = order_id
        self.order_data = order_data
        self.total_amount = 0
        self.payment_id = 0
        super().__init__()

    def run(self):
        """Call payment microservice to generate payment transaction"""
        try:
            order_response = requests.get(
                f"{config.API_GATEWAY_URL}/store-manager-api/orders/{self.order_id}"
            )
            if not order_response.ok:
                error_payload = self._safe_json(order_response)
                self.logger.error(f"Erreur {order_response.status_code} lors de la récupération de la commande : {error_payload}")
                return OrderSagaState.INCREASING_STOCK

            order_payload = order_response.json() or {}
            self.total_amount = self._parse_total_amount(order_payload.get("total_amount"))

            payment_response = requests.post(
                f"{config.API_GATEWAY_URL}/payments-api/payments",
                json={
                    "user_id": self.order_data.get("user_id"),
                    "order_id": self.order_id,
                    "total_amount": self.total_amount
                },
                headers={'Content-Type': 'application/json'}
            )
            if payment_response.ok:
                payment_payload = self._safe_json(payment_response) or {}
                self.payment_id = payment_payload.get("payment_id", 0) if isinstance(payment_payload, dict) else 0
                self.logger.debug("La création d'une transaction de paiement a réussi")
                return OrderSagaState.COMPLETED
            else:
                error_payload = self._safe_json(payment_response)
                self.logger.error(f"Erreur {payment_response.status_code} : {error_payload}")
                return OrderSagaState.INCREASING_STOCK

        except Exception as e:
            self.logger.error("La création d'une transaction de paiement a échoué : " + str(e))
            return OrderSagaState.INCREASING_STOCK
        
    def rollback(self):
        """Call payment microservice to delete payment transaction"""
        # ATTENTION: Nous pourrions utiliser cette méthode si nous avions des étapes supplémentaires, mais ce n'est pas le cas actuellement, elle restera donc INUTILISÉE.
        self.logger.debug("La suppression d'une transaction de paiement a réussi")
        return OrderSagaState.INCREASING_STOCK

    @staticmethod
    def _safe_json(response):
        try:
            return response.json()
        except Exception:
            return response.text

    @staticmethod
    def _parse_total_amount(total):
        try:
            return float(total)
        except (TypeError, ValueError):
            return 0.0
