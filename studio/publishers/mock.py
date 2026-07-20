"""Deterministic mock publisher.

Used in dev and whenever a real provider is :class:`NotConfigured`. Publishing
returns a plausible, platform-shaped permalink; metrics return realistic counts
that are *stable per post* (seeded from ``post.id``) so charts don't jitter on
every poll.
"""

from __future__ import annotations

import random

from .base import Provider

# Permalink shapes per platform. ``{handle}`` is the account handle (leading @
# stripped), ``{id}`` a deterministic remote id derived from the post.
_URL_SHAPES = {
    "INSTAGRAM": "https://www.instagram.com/p/{id}/",
    "TIKTOK": "https://www.tiktok.com/@{handle}/video/{id}",
    "YOUTUBE": "https://youtu.be/{id}",
    "X": "https://x.com/{handle}/status/{id}",
    "FACEBOOK": "https://www.facebook.com/{handle}/posts/{id}",
    "LINKEDIN": "https://www.linkedin.com/feed/update/urn:li:activity:{id}/",
    "THREADS": "https://www.threads.net/@{handle}/post/{id}",
}

_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-"


def _handle(post) -> str:
    acct = getattr(post, "social_account", None)
    raw = (getattr(acct, "handle", "") or "bcpstudio").lstrip("@")
    return raw or "bcpstudio"


def _remote_id(post) -> str:
    """A stable, platform-plausible id string seeded from the post id."""
    rng = random.Random(f"id:{post.id}")
    if post.platform in ("YOUTUBE",):
        return "".join(rng.choice(_ALPHABET) for _ in range(11))
    if post.platform in ("INSTAGRAM", "TIKTOK", "THREADS"):
        return "".join(rng.choice(_ALPHABET) for _ in range(11))
    # X / Facebook / LinkedIn use big numeric ids.
    return str(rng.randint(10**17, 10**18 - 1))


class MockProvider(Provider):
    """Always-succeeds provider for local/dev and as the registry fallback."""

    platform = None  # handles any platform

    def publish(self, post) -> dict:
        rid = _remote_id(post)
        shape = _URL_SHAPES.get(post.platform, "https://example.com/{handle}/{id}")
        url = shape.format(handle=_handle(post), id=rid)
        return {"url": url, "id": rid, "mock": True}

    def metrics(self, post) -> dict:
        """Stable, realistic-looking counts seeded from ``post.id``.

        Fields match the columns on ``studio.models.PostMetric`` so the result
        can be splatted straight into ``PostMetric.objects.create(post=..., **d)``.
        """
        rng = random.Random(f"metrics:{post.id}")
        impressions = rng.randint(1_200, 90_000)
        reach = int(impressions * rng.uniform(0.55, 0.9))
        views = int(impressions * rng.uniform(0.4, 0.95))
        likes = int(reach * rng.uniform(0.02, 0.12))
        comments = int(likes * rng.uniform(0.02, 0.15))
        shares = int(likes * rng.uniform(0.01, 0.1))
        saves = int(likes * rng.uniform(0.02, 0.2))
        clicks = int(reach * rng.uniform(0.005, 0.05))
        revenue_cents = int(views * rng.uniform(0.0, 0.6))
        return {
            "impressions": impressions,
            "reach": reach,
            "likes": likes,
            "comments": comments,
            "shares": shares,
            "saves": saves,
            "views": views,
            "clicks": clicks,
            "revenue_cents": revenue_cents,
        }
