"""Paid video platform — a self-hosted Floatplane/YouTube.

Videos are transcoded to HLS (studio/services.py) and stored locally. Access is
gated by membership tier (Stripe subscriptions). Playback uses signed/expiring
URLs so members-only content can't be hotlinked.
"""

from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone

from .commerce_models import StoreCustomer
from .models import Client


class Channel(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="channels")
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    banner_url = models.URLField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class MembershipPlan(models.Model):
    """A paid tier for a channel (Stripe subscription)."""

    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name="plans")
    name = models.CharField(max_length=120)
    tier = models.IntegerField(default=1)  # higher = more access
    amount_cents = models.IntegerField()
    currency = models.CharField(max_length=3, default="USD")
    interval = models.CharField(max_length=10, default="month")  # month | year
    perks = models.TextField(blank=True)
    stripe_price_id = models.CharField(max_length=120, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.channel.name} — {self.name}"


class Membership(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Active"
        PAST_DUE = "PAST_DUE", "Past due"
        CANCELLED = "CANCELLED", "Cancelled"

    plan = models.ForeignKey(MembershipPlan, on_delete=models.CASCADE, related_name="memberships")
    customer = models.ForeignKey(StoreCustomer, on_delete=models.CASCADE, related_name="memberships")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.ACTIVE)
    stripe_subscription_id = models.CharField(max_length=200, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.customer.email} → {self.plan.name}"

    @property
    def is_current(self):
        return self.status == "ACTIVE" and (
            not self.current_period_end or self.current_period_end >= timezone.now()
        )


class Video(models.Model):
    class Visibility(models.TextChoices):
        PUBLIC = "PUBLIC", "Public (free)"
        MEMBERS = "MEMBERS", "Members only"
        TIER = "TIER", "Specific tier+"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        TRANSCODING = "TRANSCODING", "Transcoding"
        READY = "READY", "Ready"
        FAILED = "FAILED", "Failed"

    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, related_name="videos")
    title = models.CharField(max_length=250)
    slug = models.SlugField()
    description = models.TextField(blank=True)
    # Source + transcoded output
    source_url = models.CharField(max_length=1000, blank=True)
    hls_path = models.CharField(max_length=1000, blank=True)   # local .m3u8
    thumbnail_url = models.CharField(max_length=1000, blank=True)
    duration_ms = models.IntegerField(null=True, blank=True)
    visibility = models.CharField(max_length=10, choices=Visibility.choices, default=Visibility.PUBLIC)
    min_tier = models.IntegerField(default=1)  # for TIER visibility
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("channel", "slug")
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title

    def accessible_to(self, memberships) -> bool:
        """True if the given active memberships grant access to this video."""
        if self.visibility == "PUBLIC":
            return True
        current = [m for m in memberships if m.is_current and m.plan.channel_id == self.channel_id]
        if self.visibility == "MEMBERS":
            return bool(current)
        return any(m.plan.tier >= self.min_tier for m in current)


class VideoView(models.Model):
    video = models.ForeignKey(Video, on_delete=models.CASCADE, related_name="views")
    customer = models.ForeignKey(StoreCustomer, on_delete=models.SET_NULL, null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    watched_ms = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
