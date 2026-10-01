"""Stripe integration — hosted Checkout for the store and subscription tiers.

Reuses the GritBox Stripe account via env keys (STRIPE_SECRET_KEY etc.). We use
hosted Checkout so no card data ever touches this app. If keys aren't set, the
helpers return (None, notice) and callers show a friendly "payments not
configured yet" message — the app still runs.
"""

from __future__ import annotations

from django.conf import settings
from django.utils import timezone


def _client():
    key = settings.STRIPE_SECRET_KEY
    if not key:
        return None
    import stripe

    stripe.api_key = key
    return stripe


def configured() -> bool:
    return bool(settings.STRIPE_SECRET_KEY)


def create_product_checkout(order, items, success_url, cancel_url):
    """items: list of (Price, qty). Returns (checkout_url, error)."""
    stripe = _client()
    if not stripe:
        return None, "Payments aren't configured yet (no Stripe key set)."
    line_items = []
    for price, qty in items:
        line_items.append({
            "price_data": {
                "currency": price.currency.lower(),
                "product_data": {"name": price.product.name},
                "unit_amount": price.unit_amount_cents,
            },
            "quantity": qty,
        })
    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=line_items,
            success_url=success_url,
            cancel_url=cancel_url,
            client_reference_id=str(order.id),
            metadata={"order_id": str(order.id), "kind": "store"},
        )
        order.stripe_session_id = session.id
        order.save(update_fields=["stripe_session_id"])
        return session.url, None
    except Exception as exc:  # surface Stripe errors without crashing
        return None, f"Stripe error: {exc}"


def create_subscription_checkout(plan, email, success_url, cancel_url):
    """Start a subscription for a membership plan. Returns (url, error)."""
    stripe = _client()
    if not stripe:
        return None, "Payments aren't configured yet (no Stripe key set)."
    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            line_items=[{
                "price_data": {
                    "currency": plan.currency.lower(),
                    "product_data": {"name": f"{plan.channel.name} — {plan.name}"},
                    "unit_amount": plan.amount_cents,
                    "recurring": {"interval": plan.interval},
                },
                "quantity": 1,
            }],
            customer_email=email or None,
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={"plan_id": str(plan.id), "kind": "membership"},
        )
        return session.url, None
    except Exception as exc:
        return None, f"Stripe error: {exc}"


def handle_webhook(payload: bytes, sig_header: str):
    """Process a Stripe webhook. Returns (ok, message)."""
    stripe = _client()
    if not stripe:
        return False, "no stripe"
    from . import models

    secret = settings.STRIPE_WEBHOOK_SECRET
    try:
        if secret:
            event = stripe.Webhook.construct_event(payload, sig_header, secret)
        else:  # dev without a signing secret
            import json
            event = json.loads(payload)
    except Exception as exc:
        return False, f"bad signature: {exc}"

    etype = event["type"] if isinstance(event, dict) else event.type
    obj = (event["data"]["object"] if isinstance(event, dict) else event.data.object)

    if etype == "checkout.session.completed":
        kind = (obj.get("metadata") or {}).get("kind")
        if kind == "store":
            oid = (obj.get("metadata") or {}).get("order_id")
            order = models.Order.objects.filter(id=oid).first()
            if order:
                order.status = "PAID"
                order.paid_at = timezone.now()
                order.stripe_payment_intent = obj.get("payment_intent", "")
                order.save()
        elif kind == "membership":
            pid = (obj.get("metadata") or {}).get("plan_id")
            plan = models.MembershipPlan.objects.filter(id=pid).first()
            email = obj.get("customer_details", {}).get("email") or obj.get("customer_email")
            if plan and email:
                cust, _ = models.StoreCustomer.objects.get_or_create(email=email)
                models.Membership.objects.update_or_create(
                    plan=plan, customer=cust,
                    defaults={"status": "ACTIVE",
                              "stripe_subscription_id": obj.get("subscription", "")},
                )
    return True, etype
