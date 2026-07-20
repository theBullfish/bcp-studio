"""SOCIALS & DISTRIBUTION management views.

Where staff manage each client's connected social channels, authorize the app
to act on the client's behalf, and configure how produced media is divided
across platforms (distribution rules + per-platform profiles).

Deep CRUD still lives in Django admin; these are the day-to-day management
screens, rendered on Skote's `partials/base.html`.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from . import models
from .models import Role, role_at_least


def _can(user, minimum):
    prof = getattr(user, "profile", None)
    return bool(prof) and role_at_least(prof.role, minimum)


# ---------------------------------------------------------------------------
# Overview across clients
# ---------------------------------------------------------------------------


@login_required
def distribution(request):
    """Overview: one card/row per client with channel + rule counts."""
    clients = (
        models.Client.objects.annotate(
            n_channels=Count(
                "social_accounts",
                filter=Q(social_accounts__connected=True),
                distinct=True,
            ),
            n_rules=Count("distribution_rules", distinct=True),
        )
        .order_by("name")
    )
    ctx = {
        "heading": "Channels & Distribution",
        "pageview": "Business",
        "clients": clients,
        "can_manage": _can(request.user, Role.ADMIN),
    }
    return render(request, "studio/socials/distribution.html", ctx)


# ---------------------------------------------------------------------------
# One client's channels + rules + profiles
# ---------------------------------------------------------------------------


@login_required
def dist_client(request, client_id):
    """Deep management page for one client."""
    client = get_object_or_404(models.Client, id=client_id)

    channels = client.social_accounts.order_by("platform", "handle")
    rules = client.distribution_rules.order_by("source_format")

    # Upsert-friendly map of existing profiles keyed by platform.
    existing = {p.platform: p for p in client.platform_profiles.all()}
    profiles = []
    for value, label in models.Platform.choices:
        profiles.append({
            "platform": value,
            "label": label,
            "profile": existing.get(value),
        })

    ctx = {
        "heading": f"{client.name} · Distribution",
        "pageview": "Business",
        "client": client,
        "channels": channels,
        "rules": rules,
        "profiles": profiles,
        "platforms": models.Platform.choices,
        "can_manage": _can(request.user, Role.ADMIN),
    }
    return render(request, "studio/socials/dist_client.html", ctx)


# ---------------------------------------------------------------------------
# Actions (POST)
# ---------------------------------------------------------------------------


@login_required
def channel_authorize(request, client_id):
    """Authorize the app to act on a channel (and/or add a new channel).

    The client's authorized rep grants the app permission to post on their
    behalf: this flips `connected` on, records who authorized it and when, and
    sets the auto_post preference.
    """
    client = get_object_or_404(models.Client, id=client_id)
    if request.method != "POST":
        return redirect("studio:dist_client", client_id=client.id)
    if not _can(request.user, Role.ADMIN):
        messages.error(request, "You don't have permission to authorize channels.")
        return redirect("studio:dist_client", client_id=client.id)

    platform = request.POST.get("platform")
    handle = (request.POST.get("handle") or "").strip()
    auto_post = bool(request.POST.get("auto_post"))

    if platform and handle:
        account, _created = models.SocialAccount.objects.get_or_create(
            client=client, platform=platform, handle=handle,
        )
        account.connected = True
        account.authorized_by = request.user
        account.authorized_at = timezone.now()
        account.auto_post = auto_post
        account.save()
        messages.success(
            request,
            f"Authorized {account.get_platform_display()} {account.handle} "
            f"to publish on {client.name}'s behalf.",
        )
    else:
        messages.error(request, "Pick a platform and enter a handle to authorize.")

    return redirect("studio:dist_client", client_id=client.id)


@login_required
def rule_new(request, client_id):
    """Create a distribution rule: source_format -> platforms."""
    client = get_object_or_404(models.Client, id=client_id)
    if request.method != "POST":
        return redirect("studio:dist_client", client_id=client.id)
    if not _can(request.user, Role.PRODUCER):
        messages.error(request, "You don't have permission to edit distribution rules.")
        return redirect("studio:dist_client", client_id=client.id)

    source_format = (request.POST.get("source_format") or "").strip()
    platforms = request.POST.getlist("platforms")
    auto_post = bool(request.POST.get("auto_post"))

    if source_format and platforms:
        models.DistributionRule.objects.create(
            client=client,
            source_format=source_format,
            platforms=platforms,
            auto_post=auto_post,
        )
        messages.success(request, f"Rule added: {source_format} → {', '.join(platforms)}.")
    else:
        messages.error(request, "Enter a source format and pick at least one platform.")

    return redirect("studio:dist_client", client_id=client.id)


@login_required
def rule_delete(request, rule_id):
    """Delete a distribution rule, back to its client's page."""
    rule = get_object_or_404(models.DistributionRule, id=rule_id)
    client_id = rule.client_id
    if request.method != "POST":
        return redirect("studio:dist_client", client_id=client_id)
    if not _can(request.user, Role.PRODUCER):
        messages.error(request, "You don't have permission to delete distribution rules.")
        return redirect("studio:dist_client", client_id=client_id)

    rule.delete()
    messages.success(request, "Distribution rule removed.")
    return redirect("studio:dist_client", client_id=client_id)


@login_required
def profile_save(request, client_id):
    """Upsert the PlatformProfile for (client, platform)."""
    client = get_object_or_404(models.Client, id=client_id)
    if request.method != "POST":
        return redirect("studio:dist_client", client_id=client.id)
    if not _can(request.user, Role.PRODUCER):
        messages.error(request, "You don't have permission to edit platform profiles.")
        return redirect("studio:dist_client", client_id=client.id)

    platform = request.POST.get("platform")
    valid = {v for v, _ in models.Platform.choices}
    if platform not in valid:
        messages.error(request, "Unknown platform.")
        return redirect("studio:dist_client", client_id=client.id)

    profile, _created = models.PlatformProfile.objects.get_or_create(
        client=client, platform=platform,
    )
    profile.default_hashtags = (request.POST.get("default_hashtags") or "").strip()
    profile.posting_cadence = (request.POST.get("posting_cadence") or "").strip()
    profile.best_times = (request.POST.get("best_times") or "").strip()
    if "notes" in request.POST:
        profile.notes = request.POST.get("notes") or ""
    profile.save()

    messages.success(request, f"{profile.get_platform_display()} profile saved.")
    return redirect("studio:dist_client", client_id=client.id)
