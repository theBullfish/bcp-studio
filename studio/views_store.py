"""STORE module views — Stripe commerce.

Public storefront (shop/*) plus a staff management page (store/manage/*).
Checkout is hosted by Stripe (studio/stripe_service.py); orders are fulfilled
by the webhook. If Stripe isn't configured the checkout view degrades to a
friendly "payments not configured yet" notice — the app still runs.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt

from . import models, stripe_service
from .models import Role, role_at_least


def _can(user, minimum):
    prof = getattr(user, "profile", None)
    return bool(prof) and role_at_least(prof.role, minimum)


# ---------------------------------------------------------------------------
# Public storefront
# ---------------------------------------------------------------------------


def shop(request):
    """Public storefront — all active products across every client."""
    products = (
        models.Product.objects.filter(active=True, client__active=True)
        .select_related("client")
        .prefetch_related("prices")
        .order_by("client__name", "name")
    )
    return render(
        request,
        "studio/store/shop.html",
        {"products": products, "client": None},
    )


def shop_client(request, client_slug):
    """Public storefront filtered to a single client."""
    client = get_object_or_404(models.Client, slug=client_slug)
    products = (
        models.Product.objects.filter(active=True, client=client)
        .select_related("client")
        .prefetch_related("prices")
        .order_by("name")
    )
    return render(
        request,
        "studio/store/shop_client.html",
        {"products": products, "client": client},
    )


def shop_checkout(request, product_id):
    """POST -> create Order + hand off to Stripe hosted Checkout."""
    if request.method != "POST":
        return redirect("studio:shop")

    product = get_object_or_404(models.Product, id=product_id, active=True)
    price = product.default_price
    if not price:
        messages.error(request, "This product has no price set.")
        return redirect("studio:shop")

    email = (request.POST.get("email") or "").strip()

    # Resolve / create the buyer.
    customer = None
    if email:
        customer, _ = models.StoreCustomer.objects.get_or_create(email=email)

    order = models.Order.objects.create(
        client=product.client,
        customer=customer,
        status=models.Order.Status.PENDING,
        total_cents=price.unit_amount_cents,
        currency=price.currency,
        email=email,
    )
    models.OrderItem.objects.create(
        order=order,
        product=product,
        price=price,
        quantity=1,
        unit_amount_cents=price.unit_amount_cents,
    )

    success_url = request.build_absolute_uri(reverse("studio:shop_success"))
    cancel_url = request.build_absolute_uri(reverse("studio:shop_cancel"))
    url, err = stripe_service.create_product_checkout(
        order, [(price, 1)], success_url=success_url, cancel_url=cancel_url
    )
    if url:
        return redirect(url)

    # No Stripe key (or a Stripe error) — show a friendly notice.
    return render(
        request,
        "studio/store/checkout_notice.html",
        {"order": order, "product": product, "price": price, "error": err},
    )


def shop_success(request):
    return render(request, "studio/store/success.html", {})


def shop_cancel(request):
    return render(request, "studio/store/cancel.html", {})


@csrf_exempt
def stripe_webhook(request):
    """Stripe webhook receiver. Always 200 on handled events (so Stripe stops
    retrying); 400 only on signature failure."""
    if request.method != "POST":
        return HttpResponse(status=405)

    sig = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    ok, msg = stripe_service.handle_webhook(request.body, sig)
    if not ok and isinstance(msg, str) and msg.startswith("bad signature"):
        return HttpResponse(status=400)
    return HttpResponse(status=200)


# ---------------------------------------------------------------------------
# Staff management
# ---------------------------------------------------------------------------


def _manage_context(request, **extra):
    products = (
        models.Product.objects.select_related("client")
        .prefetch_related("prices")
        .order_by("client__name", "name")
    )
    orders = (
        models.Order.objects.select_related("customer", "client")
        .order_by("-created_at")[:25]
    )
    ctx = {
        "heading": "Store",
        "pageview": "Commerce",
        "products": products,
        "orders": orders,
        "clients": models.Client.objects.filter(active=True).order_by("name"),
        "kinds": models.Product.Kind.choices,
    }
    ctx.update(extra)
    return ctx


@login_required
def store_manage(request):
    if not _can(request.user, Role.PRODUCER):
        messages.error(request, "You don't have permission to manage the store.")
        return redirect("studio:dashboard")
    return render(request, "studio/store/manage.html", _manage_context(request))


@login_required
def store_product_new(request):
    if not _can(request.user, Role.PRODUCER):
        messages.error(request, "You don't have permission to manage the store.")
        return redirect("studio:dashboard")
    if request.method != "POST":
        return redirect("studio:store_manage")

    client_id = request.POST.get("client")
    name = (request.POST.get("name") or "").strip()
    kind = request.POST.get("kind") or models.Product.Kind.PHYSICAL
    image_url = (request.POST.get("image_url") or "").strip()
    description = (request.POST.get("description") or "").strip()
    price_dollars = (request.POST.get("price_dollars") or "").strip()

    client = models.Client.objects.filter(id=client_id).first()
    if not client or not name:
        messages.error(request, "Client and product name are required.")
        return redirect("studio:store_manage")

    try:
        cents = int(round(float(price_dollars) * 100))
    except (TypeError, ValueError):
        messages.error(request, "Enter a valid price.")
        return redirect("studio:store_manage")

    product = models.Product.objects.create(
        client=client,
        name=name,
        slug=slugify(name),
        kind=kind,
        image_url=image_url,
        description=description,
    )
    models.Price.objects.create(
        product=product,
        unit_amount_cents=cents,
        currency="USD",
        active=True,
    )
    messages.success(request, f"Product “{name}” created.")
    return redirect("studio:store_manage")
