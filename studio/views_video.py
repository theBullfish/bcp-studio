"""Paid video platform views — self-hosted HLS streaming + Stripe subscriptions.

Public side (`/watch/...`): browse channels, watch videos gated by membership
tier, subscribe via Stripe Checkout. Staff side (`/videos/manage/...`): create
videos, kick off HLS transcodes. Access is decided by Video.accessible_to() over
the viewer's current memberships; playback degrades gracefully when there's no
ffmpeg (the source_url plays directly).
"""

from __future__ import annotations

import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from . import models, services, stripe_service
from .models import Role, role_at_least

VISIBILITY_BADGE = {
    "PUBLIC": "success",
    "MEMBERS": "warning",
    "TIER": "info",
}

STATUS_BADGE = {
    "DRAFT": "secondary",
    "TRANSCODING": "info",
    "READY": "success",
    "FAILED": "danger",
}


def _can(user, minimum):
    prof = getattr(user, "profile", None)
    return bool(prof) and role_at_least(prof.role, minimum)


def _viewer_memberships(request):
    """Active-or-not memberships for the signed-in viewer (matched by email).

    accessible_to() filters on m.is_current itself, so we just hand it the
    customer's memberships. Anonymous viewers get nothing.
    """
    if not request.user.is_authenticated:
        return []
    email = request.user.email
    if not email:
        return []
    customer = models.StoreCustomer.objects.filter(email=email).first()
    if not customer:
        return []
    return list(customer.memberships.select_related("plan", "plan__channel").all())


# ---------------------------------------------------------------------------
# Public — watch
# ---------------------------------------------------------------------------


def watch_home(request):
    channels = models.Channel.objects.all().order_by("name")
    return render(request, "studio/video/watch_home.html", {"channels": channels})


def watch_channel(request, slug):
    channel = get_object_or_404(models.Channel, slug=slug)
    plans = channel.plans.filter(active=True).order_by("tier", "amount_cents")
    memberships = _viewer_memberships(request)
    videos = channel.videos.all()
    cards = []
    for video in videos:
        cards.append({
            "video": video,
            "locked": video.visibility != "PUBLIC",
            "accessible": video.accessible_to(memberships),
        })
    return render(request, "studio/video/channel.html", {
        "channel": channel,
        "plans": plans,
        "videos": cards,
    })


def watch_video(request, video_id):
    video = get_object_or_404(models.Video, id=video_id)
    channel = video.channel
    memberships = _viewer_memberships(request)
    accessible = video.accessible_to(memberships)

    # Serve playback through a signed, expiring URL so members-only content
    # can't be hotlinked. Detect HLS from the underlying file, not the token URL.
    from .signing import signed_hls_url

    underlying = video.hls_path or video.source_url
    is_hls = bool(underlying) and underlying.endswith(".m3u8")
    src = signed_hls_url(video, request) if (accessible and underlying) else ""

    if accessible and src:
        # Record a view (best effort — attach customer/user when we can).
        customer = None
        if request.user.is_authenticated and request.user.email:
            customer = models.StoreCustomer.objects.filter(email=request.user.email).first()
        models.VideoView.objects.create(
            video=video,
            customer=customer,
            user=request.user if request.user.is_authenticated else None,
        )

    plans = channel.plans.filter(active=True).order_by("tier", "amount_cents")
    return render(request, "studio/video/watch.html", {
        "video": video,
        "channel": channel,
        "accessible": accessible,
        "src": src,
        "is_hls": is_hls,
        "plans": plans,
    })


@require_POST
def subscribe(request, plan_id):
    plan = get_object_or_404(models.MembershipPlan, id=plan_id)
    email = request.POST.get("email") or (
        request.user.email if request.user.is_authenticated else ""
    )
    success_url = request.build_absolute_uri(reverse("studio:sub_success"))
    cancel_url = request.build_absolute_uri(
        reverse("studio:watch_channel", args=[plan.channel.slug])
    )
    url, err = stripe_service.create_subscription_checkout(
        plan, email=email, success_url=success_url, cancel_url=cancel_url
    )
    if url:
        return redirect(url)
    return render(request, "studio/video/sub_success.html", {
        "error": err or "Payments aren't configured yet.",
        "plan": plan,
    })


def sub_success(request):
    return render(request, "studio/video/sub_success.html", {})


# ---------------------------------------------------------------------------
# Staff — manage
# ---------------------------------------------------------------------------


@login_required
def video_manage(request):
    if not _can(request.user, Role.PRODUCER):
        messages.error(request, "You don't have access to the video platform.")
        return redirect("studio:dashboard")

    channels = models.Channel.objects.all().order_by("name")
    videos = list(models.Video.objects.select_related("channel").all())
    for v in videos:
        v.viz_badge = VISIBILITY_BADGE.get(v.visibility, "secondary")
        v.stat_badge = STATUS_BADGE.get(v.status, "secondary")
    plans = models.MembershipPlan.objects.select_related("channel").order_by("channel__name", "tier")
    return render(request, "studio/video/manage.html", {
        "channels": channels,
        "videos": videos,
        "plans": plans,
        "visibilities": models.Video.Visibility.choices,
        "heading": "Videos",
        "pageview": "Platform",
    })


@login_required
@require_POST
def video_new(request):
    if not _can(request.user, Role.PRODUCER):
        messages.error(request, "You don't have permission to create videos.")
        return redirect("studio:video_manage")

    channel = get_object_or_404(models.Channel, id=request.POST.get("channel"))
    title = (request.POST.get("title") or "").strip() or "Untitled"
    visibility = request.POST.get("visibility") or models.Video.Visibility.PUBLIC
    try:
        min_tier = int(request.POST.get("min_tier") or 1)
    except (TypeError, ValueError):
        min_tier = 1

    models.Video.objects.create(
        channel=channel,
        title=title,
        slug=slugify(title)[:50] or "video",
        description=request.POST.get("description", ""),
        visibility=visibility,
        min_tier=min_tier,
        source_url=request.POST.get("source_url", ""),
        status=models.Video.Status.DRAFT,
    )
    messages.success(request, f"Created “{title}”.")
    return redirect("studio:video_manage")


@login_required
@require_POST
def video_transcode(request, video_id):
    if not _can(request.user, Role.PRODUCER):
        messages.error(request, "You don't have permission to transcode.")
        return redirect("studio:video_manage")

    video = get_object_or_404(models.Video, id=video_id)
    video.status = models.Video.Status.TRANSCODING
    video.save(update_fields=["status"])

    out_dir = os.path.join(settings.HLS_ROOT, str(video.id))
    playlist, real = services.transcode_to_hls(video.source_url, out_dir=out_dir, name="master")

    if playlist:
        video.hls_path = playlist
        video.status = models.Video.Status.READY
        video.published_at = timezone.now()
        messages.success(request, f"Transcoded “{video.title}” to HLS.")
    else:
        # No ffmpeg / no real source (demo): mark ready and play the source_url.
        video.status = models.Video.Status.READY
        if not video.published_at:
            video.published_at = timezone.now()
        messages.info(
            request,
            f"“{video.title}” is ready (no HLS render available — playing source directly).",
        )
    video.save()
    return redirect("studio:video_manage")
