"""Publisher registry — the seam ``studio.tasks`` publishes through.

``tasks.py`` imports exactly two callables from here::

    from .publishers import publish as provider_publish   # publish(post) -> dict
    from .publishers import fetch_metrics                  # fetch_metrics(post) -> dict|None

Both try the real provider for the post's platform first and fall back to the
:class:`~studio.publishers.mock.MockProvider` when the real one is
:class:`NotConfigured` (missing app creds or channel token) — so publishing
always succeeds in dev while doing the real thing in prod.
"""

from __future__ import annotations

import logging

from .base import NotConfigured, Provider
from .instagram import InstagramProvider
from .mock import MockProvider
from .tiktok import TikTokProvider
from .x import XProvider
from .youtube import YouTubeProvider

logger = logging.getLogger("studio")

_MOCK = MockProvider()

#: platform string -> real provider instance. Platforms without a real provider
#: (Facebook, LinkedIn, Threads) simply fall through to the mock.
REGISTRY: dict[str, Provider] = {
    "INSTAGRAM": InstagramProvider(),
    "TIKTOK": TikTokProvider(),
    "YOUTUBE": YouTubeProvider(),
    "X": XProvider(),
}


def get_provider(platform: str) -> Provider | None:
    """Return the real provider registered for ``platform`` (or ``None``)."""
    return REGISTRY.get(platform)


def publish(post) -> dict:
    """Publish ``post``; real provider if configured, else mock.

    Raises whatever a *configured* real provider raises on a live failure — only
    :class:`NotConfigured` falls back to the mock. Returns ``{"url":.., "id":..}``.
    """
    provider = get_provider(post.platform)
    if provider is not None:
        try:
            result = provider.publish(post)
            logger.info("published post %s via real %s provider", post.id, post.platform)
            return result
        except NotConfigured as exc:
            logger.info(
                "real %s provider not configured for post %s (%s); using mock",
                post.platform, post.id, exc,
            )
    result = _MOCK.publish(post)
    logger.info("published post %s via mock provider (%s)", post.id, post.platform)
    return result


def fetch_metrics(post) -> dict | None:
    """Return a metrics dict for ``post``; real provider if it implements it, else mock."""
    provider = get_provider(post.platform)
    if provider is not None:
        try:
            data = provider.metrics(post)
            if data is not None:
                logger.info("metrics for post %s via real %s provider", post.id, post.platform)
                return data
        except (NotImplementedError, NotConfigured):
            pass
        except Exception:  # non-critical path — never break metric polling
            logger.warning("real %s metrics failed for post %s; using mock", post.platform, post.id)
    data = _MOCK.metrics(post)
    logger.info("metrics for post %s via mock provider (%s)", post.id, post.platform)
    return data


__all__ = [
    "NotConfigured",
    "Provider",
    "REGISTRY",
    "get_provider",
    "publish",
    "fetch_metrics",
]
