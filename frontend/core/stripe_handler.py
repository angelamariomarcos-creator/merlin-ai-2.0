# frontend/core/stripe_handler.py
import os
import stripe

STRIPE_SECRET_KEY      = os.environ.get("STRIPE_SECRET_KEY", "sk_test_51TbCEXCIXI5ct4VClfgwLZc8cYL33GSMQCZJxXUcSAdeUQVVbgZZm7Eslv29rYi4Oz1OkjigNsUQNtYMts4XQaCq00J0bhg5ZZ")
STRIPE_PUBLISHABLE_KEY = os.environ.get("STRIPE_PUBLISHABLE_KEY", "pk_test_51TbCEXCIXI5ct4VCtr0E541jkBfrjnRKdh2zEGZ2r39QUoGvvQ8j8NeeU1ravdSJZ2mrtS2elMOXuXcUa0Wj52yd003dQJZpEV")
STRIPE_PRICE_ID        = os.environ.get("STRIPE_PRICE_ID", "price_1ThjHWCIXl5ct4VCmTm2Cyg3")

stripe.api_key = STRIPE_SECRET_KEY


def create_checkout_session(success_url: str, cancel_url: str) -> str:
    """Crea una sesión de Stripe Checkout y devuelve la URL de pago."""
    session = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price": STRIPE_PRICE_ID,
            "quantity": 1,
        }],
        mode="subscription",
        success_url=success_url + "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=cancel_url,
    )
    return session.url


def verify_session(session_id: str) -> bool:
    """Verifica que la sesión de pago fue completada correctamente."""
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        return session.payment_status == "paid" or session.status == "complete"
    except Exception:
        return False


def get_publishable_key() -> str:
    return STRIPE_PUBLISHABLE_KEY