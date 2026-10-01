"""Stripe webhook fulfilment (dev path: no signing secret -> json.loads body)."""

import json

import pytest

from studio import models, stripe_service

pytestmark = pytest.mark.django_db


@pytest.fixture
def order(basic_client):
    return models.Order.objects.create(
        client=basic_client,
        status=models.Order.Status.PENDING,
        total_cents=3200,
        email="buyer@x.com",
    )


def _event(order_id):
    return {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"kind": "store", "order_id": str(order_id)},
                "payment_intent": "pi_test_123",
            }
        },
    }


def test_webhook_marks_order_paid(order, settings):
    # Stripe key present (so _client() works) but no signing secret -> json path.
    settings.STRIPE_SECRET_KEY = "sk_test_dummy"
    settings.STRIPE_WEBHOOK_SECRET = ""

    payload = json.dumps(_event(order.id)).encode()
    ok, msg = stripe_service.handle_webhook(payload, sig_header="")

    assert ok is True
    assert msg == "checkout.session.completed"

    order.refresh_from_db()
    assert order.status == models.Order.Status.PAID
    assert order.paid_at is not None
    assert order.stripe_payment_intent == "pi_test_123"


def test_webhook_without_stripe_key_is_noop(order, settings):
    settings.STRIPE_SECRET_KEY = ""
    payload = json.dumps(_event(order.id)).encode()
    ok, msg = stripe_service.handle_webhook(payload, sig_header="")

    assert ok is False
    order.refresh_from_db()
    assert order.status == models.Order.Status.PENDING


def test_webhook_view_returns_200(client, order, settings):
    from django.urls import reverse

    settings.STRIPE_SECRET_KEY = "sk_test_dummy"
    settings.STRIPE_WEBHOOK_SECRET = ""
    payload = json.dumps(_event(order.id))

    resp = client.post(
        reverse("studio:stripe_webhook"),
        data=payload,
        content_type="application/json",
    )
    assert resp.status_code == 200
    order.refresh_from_db()
    assert order.status == models.Order.Status.PAID
