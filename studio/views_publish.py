"""OAuth channel-connect views.

The "log in as the client and let the app post" flow. An admin starts a connect
for a (client, platform); if the platform's app credentials are configured we
redirect into the provider's OAuth consent screen, and the callback exchanges
the ``code`` for tokens and stores them on the client's ``SocialAccount``. When
creds are NOT configured (typical in dev) we render a notice page offering a
"mark authorized (dev)" action so the whole distribution flow stays testable
without registering real OAuth apps.

Plain views; the URL names resolve under the ``studio:`` namespace because
``urls_publish`` is included from the studio URLconf.
"""

from __future__ import annotations

import logging
import os
from datetime import timedelta
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from . import models
from .models import Role, role_at_least

logger = logging.getLogger("studio")


def _can(user, minimum) -> bool:
    prof = getattr(user, "profile", None)
    return bool(prof) and role_at_least(prof.role, minimum)


# Per-platform OAuth endpoints + env credential names + default scopes.
# Meta covers Instagram/Facebook/Threads (same app + Graph OAuth dialog).
_META = {
    "authorize_url": "https://www.facebook.com/v19.0/dialog/oauth",
    "token_url": "https://graph.facebook.com/v19.0/oauth/access_token",
    "client_id_env": "META_APP_ID",
    "client_secret_env": "META_APP_SECRET",
    "client_id_param": "client_id",
    "scope": "instagram_basic,instagram_content_publish,pages_show_list,pages_read_engagement",
}

OAUTH = {
    "INSTAGRAM": _META,
    "FACEBOOK": _META,
    "THREADS": _META,
    "TIKTOK": {
        "authorize_url": "https://www.tiktok.com/v2/auth/authorize/",
        "token_url": "https://open.tiktokapis.com/v2/oauth/token/",
        "client_id_env": "TIKTOK_CLIENT_KEY",
        "client_secret_env": "TIKTOK_CLIENT_SECRET",
        "client_id_param": "client_key",
        "scope": "video.publish,video.upload,user.info.basic",
    },
    "YOUTUBE": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "client_id_env": "YOUTUBE_CLIENT_ID",
        "client_secret_env": "YOUTUBE_CLIENT_SECRET",
        "client_id_param": "client_id",
        "scope": "https://www.googleapis.com/auth/youtube.upload",
        "extra_authorize": {"access_type": "offline", "prompt": "consent"},
    },
    "X": {
        "authorize_url": "https://twitter.com/i/oauth2/authorize",
        "token_url": "https://api.twitter.com/2/oauth2/token",
        "client_id_env": "X_CLIENT_ID",
        "client_secret_env": "X_CLIENT_SECRET",
        "client_id_param": "client_id",
        "scope": "tweet.read tweet.write users.read offline.access",
    },
}

_VALID_PLATFORMS = {v for v, _ in models.Platform.choices}


def _creds(platform):
    cfg = OAUTH.get(platform)
    if not cfg:
        return None, "", ""
    return cfg, os.getenv(cfg["client_id_env"], ""), os.getenv(cfg["client_secret_env"], "")


def _redirect_uri(platform) -> str:
    return settings.SITE_URL.rstrip("/") + reverse("studio:connect_callback", args=[platform])


@login_required
def connect_start(request, client_id, platform):
    """Begin connecting a channel: redirect to OAuth, or offer the dev path."""
    client = get_object_or_404(models.Client, id=client_id)
    if not _can(request.user, Role.ADMIN):
        messages.error(request, "You don't have permission to connect channels.")
        return redirect("studio:dist_client", client_id=client.id)

    if platform not in _VALID_PLATFORMS:
        messages.error(request, "Unknown platform.")
        return redirect("studio:dist_client", client_id=client.id)

    handle = (request.POST.get("handle") or request.GET.get("handle") or "").strip()

    # Find an existing channel for this platform, else keep the supplied handle.
    account = client.social_accounts.filter(platform=platform).order_by("id").first()

    cfg, client_id_val, client_secret_val = _creds(platform)
    configured = bool(cfg and client_id_val and client_secret_val)

    # --- Dev path: explicit "mark authorized" POST -------------------------
    if request.method == "POST" and request.POST.get("mark_authorized"):
        if not account:
            if not handle:
                messages.error(request, "Enter the channel handle to authorize.")
                return redirect("studio:connect_start", client_id=client.id, platform=platform)
            account, _ = models.SocialAccount.objects.get_or_create(
                client=client, platform=platform, handle=handle,
            )
        account.connected = True
        account.authorized_by = request.user
        account.authorized_at = timezone.now()
        account.auto_post = bool(request.POST.get("auto_post"))
        account.save()
        messages.success(
            request,
            f"Marked {account.get_platform_display()} {account.handle} authorized (dev).",
        )
        return redirect("studio:dist_client", client_id=client.id)

    # --- Not configured: render the notice with the dev option -------------
    if not configured:
        return render(
            request,
            "studio/publish/connect_notice.html",
            {
                "heading": f"Connect {dict(models.Platform.choices).get(platform, platform)}",
                "pageview": "Business",
                "mode": "notice",
                "client": client,
                "platform": platform,
                "platform_label": dict(models.Platform.choices).get(platform, platform),
                "account": account,
                "handle": handle,
                "env_name": cfg["client_id_env"] if cfg else "",
            },
        )

    # --- Configured: redirect into the provider consent screen -------------
    if not account:
        account = models.SocialAccount.objects.create(
            client=client, platform=platform, handle=handle or f"pending-{platform.lower()}",
        )

    state = f"{client.id}:{account.id}"
    params = {
        cfg["client_id_param"]: client_id_val,
        "redirect_uri": _redirect_uri(platform),
        "response_type": "code",
        "scope": cfg["scope"],
        "state": state,
    }
    params.update(cfg.get("extra_authorize", {}))
    url = f"{cfg['authorize_url']}?{urlencode(params)}"
    logger.info("connect_start: redirecting %s/%s to provider OAuth", client.id, platform)
    return redirect(url)


@login_required
def connect_callback(request, platform):
    """OAuth redirect target: exchange the code for tokens and store them."""
    if platform not in _VALID_PLATFORMS:
        return _callback_error(request, platform, "Unknown platform on callback.")

    error = request.GET.get("error") or request.GET.get("error_description")
    code = request.GET.get("code")
    state = request.GET.get("state") or ""
    if error or not code:
        return _callback_error(request, platform, error or "No authorization code returned.")

    # state = "<client_id>:<account_id>"
    try:
        client_pk, account_pk = (int(x) for x in state.split(":", 1))
    except (ValueError, AttributeError):
        return _callback_error(request, platform, "Invalid or missing OAuth state.")

    account = models.SocialAccount.objects.filter(id=account_pk, client_id=client_pk).first()
    if not account:
        return _callback_error(request, platform, "The channel for this connection no longer exists.")

    cfg, client_id_val, client_secret_val = _creds(platform)
    if not (cfg and client_id_val and client_secret_val):
        return _callback_error(request, platform, "Provider credentials are not configured.")

    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": _redirect_uri(platform),
        cfg["client_id_param"]: client_id_val,
        "client_secret": client_secret_val,
    }
    try:
        resp = requests.post(
            cfg["token_url"],
            data=data,
            headers={"Accept": "application/json"},
            timeout=30,
        )
        resp.raise_for_status()
        tokens = resp.json()
    except requests.RequestException as exc:
        logger.warning("token exchange failed for %s: %s", platform, exc)
        return _callback_error(request, platform, f"Token exchange failed: {exc}")
    except ValueError:
        return _callback_error(request, platform, "Provider returned a non-JSON token response.")

    access_token = tokens.get("access_token", "")
    if not access_token:
        return _callback_error(request, platform, "Provider did not return an access token.")

    account.access_token = access_token[:500]
    account.refresh_token = (tokens.get("refresh_token", "") or "")[:500]
    expires_in = tokens.get("expires_in")
    if expires_in:
        try:
            account.token_expires = timezone.now() + timedelta(seconds=int(expires_in))
        except (TypeError, ValueError):
            account.token_expires = None
    account.scopes = (tokens.get("scope", cfg["scope"]) or "")[:500]
    account.connected = True
    account.authorized_by = request.user
    account.authorized_at = timezone.now()
    account.save()

    messages.success(
        request,
        f"Connected {account.get_platform_display()} {account.handle}.",
    )
    return redirect("studio:dist_client", client_id=account.client_id)


def _callback_error(request, platform, detail):
    logger.info("connect_callback error (%s): %s", platform, detail)
    return render(
        request,
        "studio/publish/connect_notice.html",
        {
            "heading": "Connection failed",
            "pageview": "Business",
            "mode": "error",
            "platform": platform,
            "platform_label": dict(models.Platform.choices).get(platform, platform),
            "detail": detail,
        },
    )
