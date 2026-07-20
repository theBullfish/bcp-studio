"""STORE module URLs — Stripe commerce.

Plain urlpatterns list (NO app_name). These names resolve under the `studio:`
namespace via the parent include in studio/urls.py-level wiring.
"""

from django.urls import path

from . import views_store as v

urlpatterns = [
    # Public storefront
    path("shop/", v.shop, name="shop"),
    path("shop/<slug:client_slug>/", v.shop_client, name="shop_client"),
    path("shop/product/<int:product_id>/buy/", v.shop_checkout, name="shop_checkout"),
    path("shop/success/", v.shop_success, name="shop_success"),
    path("shop/cancel/", v.shop_cancel, name="shop_cancel"),
    path("shop/webhook/", v.stripe_webhook, name="stripe_webhook"),

    # Staff management
    path("store/manage/", v.store_manage, name="store_manage"),
    path("store/manage/new/", v.store_product_new, name="store_product_new"),
]
