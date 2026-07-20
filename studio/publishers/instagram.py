"""Instagram publisher — Instagram Graph API (Content Publishing).

Real API: https://developers.facebook.com/docs/instagram-api/guides/content-publishing
Publishing is a two-step flow against the Graph API (v19.0):

  1. Create a media *container*:
       POST https://graph.facebook.com/v19.0/{ig-user-id}/media
       params: image_url|video_url, caption, media_type, access_token
  2. Publish the container:
       POST https://graph.facebook.com/v19.0/{ig-user-id}/media_publish
       params: creation_id, access_token

Requires the Meta app creds (``META_APP_ID`` / ``META_APP_SECRET``) to be set
and a page/IG access token stored on the channel's ``SocialAccount``.
"""

from __future__ import annotations

import os

import requests

from ._util import first_media_url
from .base import NotConfigured, Provider

GRAPH = "https://graph.facebook.com/v19.0"


class InstagramProvider(Provider):
    platform = "INSTAGRAM"

    def publish(self, post) -> dict:
        account = getattr(post, "social_account", None)
        token = getattr(account, "access_token", "") or ""
        app_id = os.getenv("META_APP_ID", "")
        app_secret = os.getenv("META_APP_SECRET", "")
        if not (token and app_id and app_secret):
            raise NotConfigured("Instagram: missing META app creds or channel access token")

        # The IG business user id is the channel's remote id; we keep the
        # handle-derived id here and rely on the token being page-scoped.
        ig_user_id = (account.scopes and account.handle) or account.handle
        media_url = first_media_url(post)
        caption = _compose_caption(post)

        try:
            # Step 1 — create container.
            is_video = (media_url or "").lower().endswith((".mp4", ".mov", ".m4v"))
            container_params = {
                "caption": caption,
                "access_token": token,
            }
            if is_video:
                container_params["media_type"] = "REELS"
                container_params["video_url"] = media_url
            else:
                container_params["image_url"] = media_url
            r1 = requests.post(
                f"{GRAPH}/{ig_user_id}/media", data=container_params, timeout=30
            )
            r1.raise_for_status()
            creation_id = r1.json()["id"]

            # Step 2 — publish container.
            r2 = requests.post(
                f"{GRAPH}/{ig_user_id}/media_publish",
                data={"creation_id": creation_id, "access_token": token},
                timeout=30,
            )
            r2.raise_for_status()
            media_id = r2.json()["id"]
        except requests.RequestException as exc:
            raise RuntimeError(f"Instagram publish failed: {exc}") from exc

        return {
            "url": f"https://www.instagram.com/p/{media_id}/",
            "id": str(media_id),
        }


def _compose_caption(post) -> str:
    tags = (post.hashtags or "").strip()
    body = (post.caption or "").strip()
    return f"{body}\n\n{tags}".strip() if tags else body
