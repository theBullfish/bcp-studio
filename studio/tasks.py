"""Background tasks.

In dev these run eagerly (synchronous) because no broker is configured; in
production a Celery worker + beat run them off the request path. Every task is
idempotent-safe and logs failures rather than crashing the caller.
"""

from __future__ import annotations

import logging
import os

from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("studio")


@shared_task(bind=True, max_retries=2)
def run_play_task(self, play_run_id: int):
    """Execute a queued PlayRun: produce variants, then fan out to distribution."""
    from . import models, services

    run = models.PlayRun.objects.filter(id=play_run_id).first()
    if not run:
        return {"error": "run not found"}
    run.status = "RUNNING"
    run.save(update_fields=["status"])
    project = run.project
    source = project.media.filter(derived_from__isnull=True).first()
    source_path = source.url if source and os.path.exists(source.url or "") else None
    try:
        outputs, real = services.run_play(run.play.steps, source_path=source_path, run_id=f"run{run.id}")
        created = []
        for out in outputs:
            m = models.MediaAsset.objects.create(
                project=project, kind=out["kind"], label=out["label"],
                format=out["format"], url=out.get("path", ""), status="READY",
                derived_from=source, play_run=run,
            )
            created.append(m)
        run.status = "SUCCEEDED"
        run.progress = 100
        run.finished_at = timezone.now()
        run.save()
        project.status = "READY"
        project.save(update_fields=["status"])
        # Auto-post: apply the client's distribution rules to the new variants.
        try:
            from .autopost import apply_distribution_for_run
            apply_distribution_for_run(run.id)
        except Exception as exc:  # never fail the play because posting hiccuped
            logger.warning("distribution for run %s skipped: %s", run.id, exc)
        return {"ok": True, "variants": len(created)}
    except Exception as exc:
        logger.exception("play run %s failed", play_run_id)
        run.status = "FAILED"
        run.error = str(exc)
        run.save(update_fields=["status", "error"])
        return {"error": str(exc)}


@shared_task(bind=True)
def transcode_video_task(self, video_id: int):
    from . import models, services

    video = models.Video.objects.filter(id=video_id).first()
    if not video:
        return {"error": "video not found"}
    video.status = "TRANSCODING"
    video.save(update_fields=["status"])
    out_dir = os.path.join(settings.HLS_ROOT, str(video.id))
    playlist, real = services.transcode_to_hls(video.source_url, out_dir, name="master")
    if playlist:
        video.hls_path = playlist
    video.status = "READY"
    if not video.published_at:
        video.published_at = timezone.now()
    video.save()
    return {"ok": True, "real": real}


@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def publish_post_task(self, post_id: int):
    """Publish a post via the platform provider (real if configured, else mock)."""
    from . import models

    post = models.Post.objects.filter(id=post_id).first()
    if not post:
        return {"error": "post not found"}
    post.status = "PUBLISHING"
    post.save(update_fields=["status"])
    try:
        from .publishers import publish as provider_publish

        result = provider_publish(post)
        post.external_url = result.get("url", "")
        post.status = "PUBLISHED"
        post.published_at = timezone.now()
        post.save()
        return {"ok": True, "url": post.external_url}
    except Exception as exc:
        logger.exception("publish post %s failed", post_id)
        post.status = "FAILED"
        post.failure_reason = str(exc)[:500]
        post.save(update_fields=["status", "failure_reason"])
        return {"error": str(exc)}


@shared_task
def publish_due_posts():
    """Beat task: publish any SCHEDULED post whose time has come."""
    from . import models

    now = timezone.now()
    due = models.Post.objects.filter(status="SCHEDULED", scheduled_at__lte=now)
    n = 0
    for post in due:
        publish_post_task.delay(post.id)
        n += 1
    if n:
        logger.info("enqueued %s due posts", n)
    return {"enqueued": n}


@shared_task
def poll_all_metrics():
    """Beat task: refresh performance metrics for published posts."""
    from . import models

    try:
        from .publishers import fetch_metrics
    except Exception:
        return {"skipped": "no provider"}
    updated = 0
    for post in models.Post.objects.filter(status="PUBLISHED")[:500]:
        try:
            data = fetch_metrics(post)
            if data:
                models.PostMetric.objects.create(post=post, **data)
                updated += 1
        except Exception:
            continue
    return {"updated": updated}
