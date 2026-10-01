"""X (Twitter) publisher — X API v2 (create Tweet).

Real API: https://developer.x.com/en/docs/x-api/tweets/manage-tweets/api-reference/post-tweets

  POST https://api.twitter.com/2/tweets
  Authorization: Bearer {user access token}
  body: {"text": "...", "media": {"media_ids": [...]}}

Media must first be uploaded via the v1.1 media/upload endpoint to obtain
``media_ids``; text-only posts skip that. Requires the OAuth2 app creds
(``X_CLIENT_ID`` / ``X_CLIENT_SECRET``) plus a user access token on the
channel's ``SocialAccount``.
"""

from __future__ import annotations

import os

import requests

from .base import NotConfigured, Provider

TWEETS = "https://api.twitter.com/2/tweets"


class XProvider(Provider):
    platform = "X"

    def publish(self, post) -> dict:
        account = getattr(post, "social_account", None)
        token = getattr(account, "access_token", "") or ""
        client_id = os.getenv("X_CLIENT_ID", "")
        client_secret = os.getenv("X_CLIENT_SECRET", "")
        if not (token and client_id and client_secret):
            raise NotConfigured("X: missing OAuth2 app creds or channel access token")

        caption = (post.caption or "").strip()
        tags = (post.hashtags or "").strip()
        text = f"{caption} {tags}".strip()[:280]

        try:
            resp = requests.post(
                TWEETS,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                json={"text": text},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})
            tweet_id = data.get("id", "")
        except requests.RequestException as exc:
            raise RuntimeError(f"X publish failed: {exc}") from exc

        handle = (getattr(account, "handle", "") or "i").lstrip("@")
        return {
            "url": f"https://x.com/{handle}/status/{tweet_id}",
            "id": str(tweet_id),
        }
