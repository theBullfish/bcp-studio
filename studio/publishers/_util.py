"""Small shared helpers for the real providers."""

from __future__ import annotations


def first_media_url(post) -> str:
    """Return the URL of the first attached media asset, or "".

    Posts carry media through ``PostMedia`` (ordered by ``position``). Providers
    that upload by URL use this as the asset to publish.
    """
    pm = post.media.select_related("media").order_by("position").first()
    if pm and pm.media:
        return pm.media.url or ""
    return ""
