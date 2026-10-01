"""Model behaviour: profile signal, brand kit helpers, video access, pricing."""

from datetime import timedelta

import pytest
from django.contrib.auth.models import User
from django.utils import timezone

from studio import models

pytestmark = pytest.mark.django_db


def test_profile_auto_created_for_new_user():
    user = User.objects.create_user(username="freshuser", password="pw")
    assert hasattr(user, "profile")
    assert user.profile.role == models.Role.CONTRIBUTOR


def test_superuser_profile_defaults_to_owner():
    su = User.objects.create_superuser(username="boss", email="b@x.com", password="pw")
    assert su.profile.role == models.Role.OWNER


def test_brandkit_hashtags_list():
    c = models.Client.objects.create(name="C", slug="c")
    kit = models.BrandKit.objects.create(client=c, hashtags_csv="#a, #b ,, #c ")
    assert kit.hashtags_list == ["#a", "#b", "#c"]


def test_brandkit_hashtags_list_empty():
    c = models.Client.objects.create(name="C2", slug="c2")
    kit = models.BrandKit.objects.create(client=c, hashtags_csv="")
    assert kit.hashtags_list == []


def _make_channel_video(visibility, min_tier=1):
    c = models.Client.objects.create(name="VC", slug="vc")
    channel = models.Channel.objects.create(client=c, name="Chan", slug="chan")
    video = models.Video.objects.create(
        channel=channel, title="V", slug="v",
        visibility=visibility, min_tier=min_tier, status="READY",
    )
    return channel, video


def _active_membership(channel, tier=1):
    plan = models.MembershipPlan.objects.create(
        channel=channel, name=f"T{tier}", tier=tier, amount_cents=500,
    )
    cust = models.StoreCustomer.objects.create(email=f"m{tier}@x.com")
    return models.Membership.objects.create(
        plan=plan, customer=cust, status="ACTIVE",
    )


def test_public_video_accessible_without_membership():
    _, video = _make_channel_video("PUBLIC")
    assert video.accessible_to([]) is True


def test_members_video_requires_active_membership():
    channel, video = _make_channel_video("MEMBERS")
    assert video.accessible_to([]) is False
    m = _active_membership(channel, tier=1)
    assert video.accessible_to([m]) is True


def test_members_video_rejects_cancelled_membership():
    channel, video = _make_channel_video("MEMBERS")
    m = _active_membership(channel, tier=1)
    m.status = "CANCELLED"
    m.save()
    assert video.accessible_to([m]) is False


def test_members_video_rejects_expired_period():
    channel, video = _make_channel_video("MEMBERS")
    m = _active_membership(channel, tier=1)
    m.current_period_end = timezone.now() - timedelta(days=1)
    m.save()
    assert video.accessible_to([m]) is False


def test_tier_video_needs_sufficient_tier():
    channel, video = _make_channel_video("TIER", min_tier=2)
    low = _active_membership(channel, tier=1)
    assert video.accessible_to([low]) is False
    high = _active_membership(channel, tier=2)
    assert video.accessible_to([high]) is True


def test_product_default_price_returns_first_active():
    c = models.Client.objects.create(name="Shop", slug="shop")
    prod = models.Product.objects.create(client=c, name="Thing", slug="thing")
    assert prod.default_price is None
    price = models.Price.objects.create(product=prod, unit_amount_cents=999, active=True)
    assert prod.default_price == price


def test_product_default_price_ignores_inactive():
    c = models.Client.objects.create(name="Shop2", slug="shop2")
    prod = models.Product.objects.create(client=c, name="Thing2", slug="thing2")
    models.Price.objects.create(product=prod, unit_amount_cents=500, active=False)
    assert prod.default_price is None
