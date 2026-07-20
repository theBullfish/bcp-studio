"""Store models — products sold through Stripe Checkout.

Reuses the GritBox Stripe account (keys from env/secrets, never hardcoded).
Stripe Checkout is hosted, so we never touch card data. Orders are fulfilled
by the Stripe webhook (studio/stripe_service.py).
"""

from django.contrib.auth.models import User
from django.db import models

from .models import Client


class Product(models.Model):
    class Kind(models.TextChoices):
        PHYSICAL = "PHYSICAL", "Physical"
        DIGITAL = "DIGITAL", "Digital download"
        TICKET = "TICKET", "Ticket"
        BUNDLE = "BUNDLE", "Bundle"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="products")
    name = models.CharField(max_length=200)
    slug = models.SlugField()
    description = models.TextField(blank=True)
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.PHYSICAL)
    image_url = models.URLField(blank=True)
    active = models.BooleanField(default=True)
    stripe_product_id = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("client", "slug")

    def __str__(self):
        return self.name

    @property
    def default_price(self):
        return self.prices.filter(active=True).first()


class Price(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="prices")
    unit_amount_cents = models.IntegerField()
    currency = models.CharField(max_length=3, default="USD")
    recurring = models.BooleanField(default=False)
    interval = models.CharField(max_length=10, blank=True)  # month | year
    stripe_price_id = models.CharField(max_length=120, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.product.name} — {self.unit_amount_cents/100:.2f} {self.currency}"


class StoreCustomer(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=200, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    stripe_customer_id = models.CharField(max_length=120, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email


class Order(models.Model):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        PAID = "PAID", "Paid"
        FULFILLED = "FULFILLED", "Fulfilled"
        REFUNDED = "REFUNDED", "Refunded"
        CANCELLED = "CANCELLED", "Cancelled"

    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, related_name="orders")
    customer = models.ForeignKey(StoreCustomer, on_delete=models.SET_NULL, null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    total_cents = models.IntegerField(default=0)
    currency = models.CharField(max_length=3, default="USD")
    stripe_session_id = models.CharField(max_length=200, blank=True)
    stripe_payment_intent = models.CharField(max_length=200, blank=True)
    email = models.EmailField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Order #{self.pk} — {self.get_status_display()}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True)
    price = models.ForeignKey(Price, on_delete=models.SET_NULL, null=True)
    quantity = models.IntegerField(default=1)
    unit_amount_cents = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.quantity}× {self.product}"
