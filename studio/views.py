"""BCP Studio front-end views.

Every page renders through Skote's `partials/base.html`, using Skote's real
components (cards, ApexCharts, DataTables, FullCalendar, chat UI) fed by our data.
Deep CRUD lives in Django admin; these views are the day-to-day flow.
"""

from __future__ import annotations

import json
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Count, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.http import require_POST

from . import models, services
from .models import Role, role_at_least

PLATFORM_COLORS = {
    "INSTAGRAM": "#E1306C",
    "TIKTOK": "#00b8b0",
    "YOUTUBE": "#FF0000",
    "X": "#111111",
    "FACEBOOK": "#1877F2",
    "LINKEDIN": "#0A66C2",
    "THREADS": "#333333",
}

STATUS_BADGE = {
    "DRAFT": "secondary",
    "IN_REVIEW": "warning",
    "APPROVED": "info",
    "SCHEDULED": "primary",
    "PUBLISHING": "info",
    "PUBLISHED": "success",
    "FAILED": "danger",
    "REJECTED": "danger",
}


def _role(user) -> str:
    prof = getattr(user, "profile", None)
    return prof.role if prof else Role.VIEWER


def _can(user, minimum: str) -> bool:
    return role_at_least(_role(user), minimum)


def _cents(val) -> int:
    return val or 0


# ---------------------------------------------------------------------------
# Control Room (dashboard)
# ---------------------------------------------------------------------------


@login_required
def dashboard(request):
    now = timezone.now()
    in30 = now + timedelta(days=30)

    revenue_total = _cents(models.RevenueEntry.objects.aggregate(s=Sum("amount_cents"))["s"])
    metric_totals = models.PostMetric.objects.aggregate(
        impressions=Sum("impressions"), views=Sum("views"), likes=Sum("likes")
    )

    months, rev_series = [], []
    for i in range(5, -1, -1):
        start = (now.replace(day=1) - timedelta(days=31 * i)).replace(day=1)
        nxt = (start + timedelta(days=32)).replace(day=1)
        total = _cents(
            models.RevenueEntry.objects.filter(
                occurred_at__gte=start, occurred_at__lt=nxt
            ).aggregate(s=Sum("amount_cents"))["s"]
        )
        months.append(start.strftime("%b"))
        rev_series.append(round(total / 100, 2))

    recent_posts = list(
        models.Post.objects.select_related("client").order_by("-updated_at")[:6]
    )
    for p in recent_posts:
        p.badge = STATUS_BADGE.get(p.status, "secondary")
        p.dot = PLATFORM_COLORS.get(p.platform, "#999")

    upcoming = list(
        models.Release.objects.select_related("client")
        .filter(release_date__gte=now, release_date__lte=in30)
        .order_by("release_date")[:6]
    )
    trends = list(models.TrendItem.objects.order_by("-captured_at")[:6])

    ctx = {
        "heading": "Control Room",
        "pageview": "Studio",
        "revenue_total": revenue_total / 100,
        "impressions": metric_totals["impressions"] or 0,
        "views": metric_totals["views"] or 0,
        "likes": metric_totals["likes"] or 0,
        "active_projects": models.Project.objects.exclude(status="ARCHIVED").count(),
        "scheduled_posts": models.Post.objects.filter(status="SCHEDULED").count(),
        "pending_approvals": models.Approval.objects.filter(decision="PENDING").count(),
        "recent_posts": recent_posts,
        "upcoming": upcoming,
        "trends": trends,
        "rev_months": json.dumps(months),
        "rev_series": json.dumps(rev_series),
    }
    return render(request, "studio/dashboard.html", ctx)


# ---------------------------------------------------------------------------
# Clients / brands
# ---------------------------------------------------------------------------


@login_required
def clients_list(request):
    clients = (
        models.Client.objects.select_related("brand_kit")
        .annotate(n_projects=Count("projects", distinct=True), n_social=Count("social_accounts", distinct=True))
        .order_by("name")
    )
    return render(
        request,
        "studio/clients_list.html",
        {"heading": "Clients", "pageview": "Studio", "clients": clients, "can_manage": _can(request.user, Role.ADMIN)},
    )


@login_required
@require_POST
def client_create(request):
    if not _can(request.user, Role.ADMIN):
        messages.error(request, "You don't have permission to add clients.")
        return redirect("studio:clients")
    name = request.POST.get("name", "").strip()
    if not name:
        messages.error(request, "Name is required.")
        return redirect("studio:clients")
    client = models.Client.objects.create(name=name, slug=slugify(name))
    models.BrandKit.objects.create(client=client)
    messages.success(request, f"Client “{name}” created.")
    return redirect("studio:client_detail", client_id=client.id)


@login_required
def client_detail(request, client_id):
    client = get_object_or_404(models.Client, id=client_id)
    kit, _ = models.BrandKit.objects.get_or_create(client=client)
    ctx = {
        "heading": client.name,
        "pageview": "Clients",
        "client": client,
        "kit": kit,
        "socials": client.social_accounts.all(),
        "assets": client.assets.all(),
        "platforms": models.Platform.choices,
        "can_manage": _can(request.user, Role.ADMIN),
    }
    return render(request, "studio/client_detail.html", ctx)


@login_required
@require_POST
def brand_kit_update(request, client_id):
    client = get_object_or_404(models.Client, id=client_id)
    if not _can(request.user, Role.ADMIN):
        messages.error(request, "You don't have permission to edit the brand kit.")
        return redirect("studio:client_detail", client_id=client.id)
    kit, _ = models.BrandKit.objects.get_or_create(client=client)
    for field in [
        "primary_color", "secondary_color", "accent_color", "font_heading",
        "font_body", "logo_url", "logo_mark_url", "watermark_url",
        "tone_of_voice", "hashtags_csv",
    ]:
        if field in request.POST:
            setattr(kit, field, request.POST.get(field, ""))
    kit.save()
    messages.success(request, "Brand kit saved.")
    return redirect("studio:client_detail", client_id=client.id)


@login_required
@require_POST
def social_add(request, client_id):
    client = get_object_or_404(models.Client, id=client_id)
    if not _can(request.user, Role.ADMIN):
        return redirect("studio:client_detail", client_id=client.id)
    platform = request.POST.get("platform")
    handle = request.POST.get("handle", "").strip()
    if platform and handle:
        models.SocialAccount.objects.get_or_create(
            client=client, platform=platform, handle=handle,
            defaults={"connected": True},
        )
        messages.success(request, "Social account connected.")
    return redirect("studio:client_detail", client_id=client.id)


# ---------------------------------------------------------------------------
# Projects & media
# ---------------------------------------------------------------------------


@login_required
def projects_list(request):
    projects = (
        models.Project.objects.select_related("client", "owner")
        .annotate(n_media=Count("media"))
        .order_by("-updated_at")
    )
    for p in projects:
        p.badge = {"DRAFT": "secondary", "PROCESSING": "warning", "READY": "success",
                   "SCHEDULED": "primary", "ARCHIVED": "dark"}.get(p.status, "secondary")
    return render(
        request,
        "studio/projects_list.html",
        {"heading": "Projects", "pageview": "Studio", "projects": projects,
         "clients": models.Client.objects.all(), "can_create": _can(request.user, Role.PRODUCER)},
    )


@login_required
@require_POST
def project_create(request):
    if not _can(request.user, Role.PRODUCER):
        messages.error(request, "You don't have permission to create projects.")
        return redirect("studio:projects")
    client = get_object_or_404(models.Client, id=request.POST.get("client"))
    project = models.Project.objects.create(
        client=client,
        owner=request.user,
        title=request.POST.get("title", "Untitled").strip() or "Untitled",
        summary=request.POST.get("summary", "").strip(),
    )
    messages.success(request, "Project created.")
    return redirect("studio:project_detail", project_id=project.id)


@login_required
def project_detail(request, project_id):
    project = get_object_or_404(models.Project.objects.select_related("client"), id=project_id)
    source_media = project.media.filter(derived_from__isnull=True)
    derived = project.media.filter(derived_from__isnull=False).select_related("play_run", "play_run__play")
    ctx = {
        "heading": project.title,
        "pageview": "Projects",
        "project": project,
        "source_media": source_media,
        "derived": derived,
        "plays": models.Play.objects.filter(active=True),
        "runs": project.play_runs.select_related("play").order_by("-created_at")[:10],
        "can_run": _can(request.user, Role.PRODUCER),
    }
    return render(request, "studio/project_detail.html", ctx)


@login_required
@require_POST
def media_add(request, project_id):
    project = get_object_or_404(models.Project, id=project_id)
    models.MediaAsset.objects.create(
        project=project,
        uploader=request.user,
        kind=request.POST.get("kind", "VIDEO"),
        label=request.POST.get("label", "Source media").strip() or "Source media",
        url=request.POST.get("url", "").strip(),
        status="READY",
    )
    messages.success(request, "Media added.")
    return redirect("studio:project_detail", project_id=project.id)


@login_required
@require_POST
def play_run(request, project_id):
    project = get_object_or_404(models.Project, id=project_id)
    if not _can(request.user, Role.PRODUCER):
        messages.error(request, "You don't have permission to run plays.")
        return redirect("studio:project_detail", project_id=project.id)
    play = get_object_or_404(models.Play, id=request.POST.get("play"))
    run = models.PlayRun.objects.create(
        play=play, project=project, triggered_by=request.user, status="RUNNING"
    )
    source = project.media.filter(derived_from__isnull=True).first()
    try:
        outputs, real = services.run_play(play.steps, run_id=f"run{run.id}")
        for out in outputs:
            models.MediaAsset.objects.create(
                project=project,
                kind=out["kind"],
                label=out["label"],
                format=out["format"],
                url=out.get("path", ""),
                status="READY",
                derived_from=source,
                play_run=run,
            )
        run.status = "SUCCEEDED"
        run.progress = 100
        run.finished_at = timezone.now()
        run.save()
        project.status = "READY"
        project.save(update_fields=["status"])
        messages.success(request, f"“{play.name}” produced {len(outputs)} variants.")
    except Exception as exc:  # keep the run recoverable
        run.status = "FAILED"
        run.error = str(exc)
        run.save()
        messages.error(request, f"Play failed: {exc}")
    return redirect("studio:project_detail", project_id=project.id)


# ---------------------------------------------------------------------------
# Plays
# ---------------------------------------------------------------------------


@login_required
def plays_list(request):
    plays = models.Play.objects.annotate(n_runs=Count("runs")).order_by("-builtin", "name")
    return render(request, "studio/plays_list.html",
                  {"heading": "AI Plays", "pageview": "Studio", "plays": plays})


# ---------------------------------------------------------------------------
# Posts / schedule
# ---------------------------------------------------------------------------


@login_required
def posts_list(request):
    status = request.GET.get("status", "")
    qs = models.Post.objects.select_related("client").order_by("-updated_at")
    if status:
        qs = qs.filter(status=status)
    posts = list(qs)
    for p in posts:
        p.badge = STATUS_BADGE.get(p.status, "secondary")
        p.dot = PLATFORM_COLORS.get(p.platform, "#999")
    ctx = {
        "heading": "Posts & Schedule",
        "pageview": "Studio",
        "posts": posts,
        "status": status,
        "statuses": models.Post.Status.choices,
        "can_draft": _can(request.user, Role.CONTRIBUTOR),
    }
    return render(request, "studio/posts_list.html", ctx)


@login_required
def post_compose(request):
    if request.method == "POST":
        client = get_object_or_404(models.Client, id=request.POST.get("client"))
        platform = request.POST.get("platform")
        action = request.POST.get("action", "draft")
        scheduled = request.POST.get("scheduled_at") or None
        social = models.SocialAccount.objects.filter(client=client, platform=platform).first()
        status = "SCHEDULED" if (action == "schedule" and scheduled) else "DRAFT"
        post = models.Post.objects.create(
            client=client,
            project_id=request.POST.get("project") or None,
            author=request.user,
            social_account=social,
            platform=platform,
            caption=request.POST.get("caption", "").strip(),
            caption_ai=request.POST.get("caption", "").strip(),
            hashtags=request.POST.get("hashtags", "").strip(),
            scheduled_at=scheduled,
            status=status,
        )
        messages.success(request, "Post created.")
        return redirect("studio:post_detail", post_id=post.id)

    clients = models.Client.objects.select_related("brand_kit").all()
    ctx = {
        "heading": "Compose Post",
        "pageview": "Posts",
        "clients": clients,
        "projects": models.Project.objects.all(),
        "platforms": models.Platform.choices,
    }
    return render(request, "studio/post_compose.html", ctx)


@login_required
@require_POST
def caption_generate(request):
    """AJAX: auto-write a caption from a summary, brand-tone aware."""
    data = json.loads(request.body or "{}")
    client = models.Client.objects.filter(id=data.get("client")).select_related("brand_kit").first()
    tone = getattr(getattr(client, "brand_kit", None), "tone_of_voice", "") if client else ""
    tags = getattr(getattr(client, "brand_kit", None), "hashtags_csv", "") if client else ""
    result = services.generate_caption(
        summary=data.get("summary", ""),
        platform=data.get("platform", "INSTAGRAM"),
        tone=tone,
        hashtags=tags,
    )
    return JsonResponse(result)


@login_required
def post_detail(request, post_id):
    post = get_object_or_404(
        models.Post.objects.select_related("client", "author"), id=post_id
    )
    post.badge = STATUS_BADGE.get(post.status, "secondary")
    ctx = {
        "heading": "Post",
        "pageview": "Posts",
        "post": post,
        "approvals": post.approvals.select_related("reviewer").all(),
        "metrics": post.metrics.order_by("-captured_at").first(),
        "can_schedule": _can(request.user, Role.PRODUCER),
        "can_approve": _can(request.user, Role.APPROVER),
    }
    return render(request, "studio/post_detail.html", ctx)


@login_required
@require_POST
def post_update(request, post_id):
    post = get_object_or_404(models.Post, id=post_id)
    post.caption = request.POST.get("caption", post.caption)
    post.hashtags = request.POST.get("hashtags", post.hashtags)
    post.save(update_fields=["caption", "hashtags", "updated_at"])
    messages.success(request, "Post updated.")
    return redirect("studio:post_detail", post_id=post.id)


@login_required
@require_POST
def post_submit_review(request, post_id):
    post = get_object_or_404(models.Post, id=post_id)
    reviewers = User.objects.filter(profile__role__in=["APPROVER", "ADMIN", "OWNER"])
    for r in reviewers:
        models.Approval.objects.get_or_create(post=post, reviewer=r)
        models.Notification.objects.create(
            user=r, kind="approval_requested",
            title="A post needs your approval",
            link=f"/posts/{post.id}/",
        )
    post.status = "IN_REVIEW"
    post.save(update_fields=["status", "updated_at"])
    messages.success(request, "Sent for approval.")
    return redirect("studio:post_detail", post_id=post.id)


@login_required
@require_POST
def post_publish(request, post_id):
    post = get_object_or_404(models.Post, id=post_id)
    if not _can(request.user, Role.PRODUCER):
        messages.error(request, "You don't have permission to publish.")
        return redirect("studio:post_detail", post_id=post.id)
    handle = post.social_account.handle if post.social_account else post.client.slug
    post.status = "PUBLISHED"
    post.published_at = timezone.now()
    post.external_url = f"https://{post.platform.lower()}.com/{handle.lstrip('@')}/p/demo{post.id}"
    post.save(update_fields=["status", "published_at", "external_url", "updated_at"])
    messages.success(request, "Published! (mock provider — real platform posting is a later phase)")
    return redirect("studio:post_detail", post_id=post.id)


# ---------------------------------------------------------------------------
# Approvals
# ---------------------------------------------------------------------------


@login_required
def approvals_list(request):
    mine = models.Approval.objects.filter(
        reviewer=request.user, decision="PENDING"
    ).select_related("post", "post__client")
    all_pending = None
    if _can(request.user, Role.ADMIN):
        all_pending = models.Approval.objects.filter(decision="PENDING").select_related(
            "post", "post__client", "reviewer"
        )
    return render(
        request,
        "studio/approvals_list.html",
        {"heading": "Approvals", "pageview": "Studio", "mine": mine,
         "all_pending": all_pending, "can_approve": _can(request.user, Role.APPROVER)},
    )


@login_required
@require_POST
def approval_decide(request, approval_id):
    approval = get_object_or_404(models.Approval, id=approval_id)
    if not _can(request.user, Role.APPROVER) or (
        approval.reviewer_id != request.user.id and not _can(request.user, Role.ADMIN)
    ):
        messages.error(request, "You can't act on this approval.")
        return redirect("studio:approvals")
    decision = request.POST.get("decision")
    approval.decision = decision
    approval.comment = request.POST.get("comment", "")
    approval.decided_at = timezone.now()
    approval.save()

    post = approval.post
    decisions = list(post.approvals.values_list("decision", flat=True))
    if "REJECTED" in decisions:
        post.status = "REJECTED"
    elif decisions and all(d == "APPROVED" for d in decisions):
        post.status = "SCHEDULED" if post.scheduled_at else "APPROVED"
    post.save(update_fields=["status", "updated_at"])
    if post.author:
        models.Notification.objects.create(
            user=post.author, kind="approval_decided",
            title=f"Your post was {decision.lower()}",
            link=f"/posts/{post.id}/",
        )
    messages.success(request, f"Marked {decision.lower()}.")
    return redirect("studio:approvals")


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------


@login_required
def calendar(request):
    scope = request.GET.get("scope", "company")
    return render(request, "studio/calendar.html",
                  {"heading": "Calendar", "pageview": "Studio", "scope": scope})


@login_required
def calendar_events(request):
    """FullCalendar JSON feed. scope=mine -> only primary release dates."""
    scope = request.GET.get("scope", "company")
    events = []
    releases = models.Release.objects.select_related("client")
    if scope == "mine":
        releases = releases.filter(is_primary=True)
    for r in releases:
        events.append({
            "title": f"🎵 {r.title}",
            "start": r.release_date.isoformat(),
            "className": "bg-primary text-white",
            "url": f"/projects/{r.project_id}/" if r.project_id else "",
        })
    if scope == "company":
        for e in models.CalendarEvent.objects.all():
            color = {"MEETING": "bg-info", "DEADLINE": "bg-danger", "SHOOT": "bg-warning",
                     "HOLD": "bg-secondary"}.get(e.kind, "bg-success")
            events.append({
                "title": e.title,
                "start": e.start.isoformat(),
                "end": e.end.isoformat() if e.end else None,
                "className": f"{color} text-white",
                "allDay": e.all_day,
            })
    return JsonResponse(events, safe=False)


# ---------------------------------------------------------------------------
# Analytics (private)
# ---------------------------------------------------------------------------


@login_required
def analytics(request):
    now = timezone.now()
    by_source = (
        models.RevenueEntry.objects.values("source")
        .annotate(total=Sum("amount_cents")).order_by("-total")
    )
    src_labels = [s["source"].title() for s in by_source]
    src_values = [round((s["total"] or 0) / 100, 2) for s in by_source]

    months, rev_series = [], []
    for i in range(5, -1, -1):
        start = (now.replace(day=1) - timedelta(days=31 * i)).replace(day=1)
        nxt = (start + timedelta(days=32)).replace(day=1)
        total = _cents(models.RevenueEntry.objects.filter(
            occurred_at__gte=start, occurred_at__lt=nxt).aggregate(s=Sum("amount_cents"))["s"])
        months.append(start.strftime("%b"))
        rev_series.append(round(total / 100, 2))

    totals = models.PostMetric.objects.aggregate(
        impressions=Sum("impressions"), reach=Sum("reach"), likes=Sum("likes"),
        comments=Sum("comments"), shares=Sum("shares"), views=Sum("views"),
    )
    top_posts = list(
        models.Post.objects.filter(status="PUBLISHED")
        .annotate(v=Sum("metrics__views")).order_by("-v")[:8]
    )
    for p in top_posts:
        p.dot = PLATFORM_COLORS.get(p.platform, "#999")

    ctx = {
        "heading": "Analytics",
        "pageview": "Studio",
        "src_labels": json.dumps(src_labels),
        "src_values": json.dumps(src_values),
        "rev_months": json.dumps(months),
        "rev_series": json.dumps(rev_series),
        "totals": totals,
        "revenue_total": _cents(models.RevenueEntry.objects.aggregate(s=Sum("amount_cents"))["s"]) / 100,
        "top_posts": top_posts,
        "can_view_pay": _can(request.user, Role.ADMIN),
        "pay_entries": models.PayEntry.objects.select_related("user").all() if _can(request.user, Role.ADMIN) else None,
    }
    return render(request, "studio/analytics.html", ctx)


# ---------------------------------------------------------------------------
# Messaging
# ---------------------------------------------------------------------------


@login_required
def messages_view(request):
    convos = request.user.conversations.prefetch_related("messages", "participants").all()
    active_id = request.GET.get("c")
    active = None
    if active_id:
        active = convos.filter(id=active_id).first()
    if not active:
        active = convos.first()
    return render(request, "studio/messages.html",
                  {"heading": "Messages", "pageview": "Studio", "convos": convos, "active": active})


@login_required
@require_POST
def message_send(request, conversation_id):
    convo = get_object_or_404(models.Conversation, id=conversation_id, participants=request.user)
    body = request.POST.get("body", "").strip()
    if body:
        models.Message.objects.create(conversation=convo, sender=request.user, body=body)
        convo.save(update_fields=["updated_at"])
    return redirect(f"/messages/?c={convo.id}")


# ---------------------------------------------------------------------------
# Team
# ---------------------------------------------------------------------------


@login_required
def team_list(request):
    users = User.objects.select_related("profile").order_by("-is_active", "username")
    return render(
        request,
        "studio/team.html",
        {"heading": "Team", "pageview": "Studio", "members": users,
         "roles": Role.choices, "can_manage": _can(request.user, Role.ADMIN),
         "can_view_pay": _can(request.user, Role.ADMIN)},
    )


@login_required
@require_POST
def team_update(request, user_id):
    if not _can(request.user, Role.ADMIN):
        messages.error(request, "You don't have permission to manage the team.")
        return redirect("studio:team")
    member = get_object_or_404(User, id=user_id)
    profile = member.profile
    if request.POST.get("role"):
        profile.role = request.POST["role"]
    if request.POST.get("pay_rate_cents"):
        profile.pay_rate_cents = int(request.POST["pay_rate_cents"])
    profile.save()
    member.is_active = "active" in request.POST
    member.save(update_fields=["is_active"])
    messages.success(request, f"Updated {member.username}.")
    return redirect("studio:team")
