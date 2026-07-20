"""TikTok publisher — Content Posting API (v2).

Real API: https://developers.tiktok.com/doc/content-posting-api-reference-direct-post
Direct-post of a video is initiated with:

  POST https://open.tiktokapis.com/v2/post/publish/video/init/
  Authorization: Bearer {access_token}
  body: {"post_info": {...}, "source_info": {"source": "PULL_FROM_URL",
         "video_url": ...}}

Requires the app creds (``TIKTOK_CLIENT_KEY`` / ``TIKTOK_CLIENT_SECRET``) plus a
user access token on the channel's ``SocialAccount``.
"""

from __future__ import annotations

import os

import requests

from ._util import first_media_url
from .base import NotConfigured, Provider

INIT = "https://open.tiktokapis.com/v2/post/publish/video/init/"


class TikTokProvider(Provider):
    platform = "TIKTOK"

    def publish(self, post) -> dict:
        account = getattr(post, "social_account", None)
        token = getattr(account, "access_token", "") or ""
        client_key = os.getenv("TIKTOK_CLIENT_KEY", "")
        client_secret = os.getenv("TIKTOK_CLIENT_SECRET", "")
        if not (token and client_key and client_secret):
            raise NotConfigured("TikTok: missing app creds or channel access token")

        media_url = first_media_url(post)
        caption = (post.caption or "").strip()
        tags = (post.hashtags or "").strip()
        title = f"{caption} {tags}".strip()[:2200]

        payload = {
            "post_info": {
                "title": title,
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_comment": False,
                "disable_duet": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": media_url,
            },
        }
        try:
            resp = requests.post(
                INIT,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json; charset=UTF-8",
                },
                json=payload,
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})
            publish_id = data.get("publish_id", "")
        except requests.RequestException as exc:
            raise RuntimeError(f"TikTok publish failed: {exc}") from exc

        handle = (getattr(account, "handle", "") or "").lstrip("@")
        return {
            "url": f"https://www.tiktok.com/@{handle}",
            "id": str(publish_id),
        }
