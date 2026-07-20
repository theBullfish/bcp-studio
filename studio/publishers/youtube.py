"""YouTube publisher — YouTube Data API v3 (videos.insert).

Real API: https://developers.google.com/youtube/v3/docs/videos/insert
A resumable/direct upload is a multipart POST:

  POST https://www.googleapis.com/upload/youtube/v3/videos?part=snippet,status&uploadType=multipart
  Authorization: Bearer {access_token}
  multipart body: metadata (snippet/status JSON) + the video bytes

Requires the OAuth app creds (``YOUTUBE_CLIENT_ID`` / ``YOUTUBE_CLIENT_SECRET``)
plus a user access token on the channel's ``SocialAccount``.
"""

from __future__ import annotations

import os

import requests

from ._util import first_media_url
from .base import NotConfigured, Provider

UPLOAD = "https://www.googleapis.com/upload/youtube/v3/videos"


class YouTubeProvider(Provider):
    platform = "YOUTUBE"

    def publish(self, post) -> dict:
        account = getattr(post, "social_account", None)
        token = getattr(account, "access_token", "") or ""
        client_id = os.getenv("YOUTUBE_CLIENT_ID", "")
        client_secret = os.getenv("YOUTUBE_CLIENT_SECRET", "")
        if not (token and client_id and client_secret):
            raise NotConfigured("YouTube: missing OAuth app creds or channel access token")

        media_url = first_media_url(post)
        caption = (post.caption or "").strip()
        tags = [t.strip("# ") for t in (post.hashtags or "").split() if t.strip("# ")]
        title = (caption.split("\n", 1)[0] or "New from BCP Studio")[:100]

        metadata = {
            "snippet": {
                "title": title,
                "description": f"{caption}\n\n{post.hashtags or ''}".strip(),
                "tags": tags,
                "categoryId": "10",  # Music
            },
            "status": {"privacyStatus": "public", "selfDeclaredMadeForKids": False},
        }
        try:
            # Pull the rendered asset, then upload it to YouTube.
            src = requests.get(media_url, timeout=60)
            src.raise_for_status()
            files = {
                "metadata": (None, __import__("json").dumps(metadata), "application/json"),
                "file": ("video.mp4", src.content, "video/*"),
            }
            resp = requests.post(
                UPLOAD,
                params={"part": "snippet,status", "uploadType": "multipart"},
                headers={"Authorization": f"Bearer {token}"},
                files=files,
                timeout=300,
            )
            resp.raise_for_status()
            video_id = resp.json().get("id", "")
        except requests.RequestException as exc:
            raise RuntimeError(f"YouTube publish failed: {exc}") from exc

        return {
            "url": f"https://youtu.be/{video_id}",
            "id": str(video_id),
        }
