"""Video access gating via memberships (integration-style, real objects)."""

import pytest

from studio import models

pytestmark = pytest.mark.django_db


@pytest.fixture
def channel(basic_client):
    return models.Channel.objects.create(client=basic_client, name="TV", slug="tv")


def _plan(channel, tier):
    return models.MembershipPlan.objects.create(
        channel=channel, name=f"Tier {tier}", tier=tier, amount_cents=500 * tier,
    )


def _membership(plan, email="viewer@x.com", status="ACTIVE"):
    cust, _ = models.StoreCustomer.objects.get_or_create(email=email)
    return models.Membership.objects.create(plan=plan, customer=cust, status=status)


def test_members_video_blocked_without_membership(channel):
    video = models.Video.objects.create(
        channel=channel, title="Members Cut", slug="mc", visibility="MEMBERS",
    )
    assert video.accessible_to([]) is False


def test_members_video_allowed_with_active_membership(channel):
    video = models.Video.objects.create(
        channel=channel, title="Members Cut", slug="mc", visibility="MEMBERS",
    )
    m = _membership(_plan(channel, 1))
    assert video.accessible_to([m]) is True


def test_membership_on_other_channel_does_not_grant_access(basic_client, channel):
    other_channel = models.Channel.objects.create(
        client=basic_client, name="Other", slug="other",
    )
    video = models.Video.objects.create(
        channel=channel, title="Members Cut", slug="mc", visibility="MEMBERS",
    )
    m = _membership(_plan(other_channel, 1))
    assert video.accessible_to([m]) is False


def test_tier_video_requires_min_tier(channel):
    video = models.Video.objects.create(
        channel=channel, title="Backstage", slug="bs", visibility="TIER", min_tier=2,
    )
    tier1 = _membership(_plan(channel, 1), email="t1@x.com")
    assert video.accessible_to([tier1]) is False
    tier2 = _membership(_plan(channel, 2), email="t2@x.com")
    assert video.accessible_to([tier2]) is True
