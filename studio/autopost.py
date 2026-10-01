"""Auto-post distribution engine.

After a :class:`~studio.models.PlayRun` produces its variant media, the run task
calls :func:`apply_distribution_for_run`. It reads the client's active
:class:`~studio.models.DistributionRule` rows, matches each rule's
``source_format`` against the produced variants, and materialises one
:class:`~studio.models.Post` per (matching format × platform) — attaching the
variant, writing an AI caption, and either scheduling it for auto-publish or
leaving it as a draft for manual review.

Idempotent: re-running for the same PlayRun will not create duplicate posts. A
(platform, source_format) is considered already-handled if a Post already exists
whose attached media belongs to this run.
"""

from __future__ import annotations

import logging

from django.utils import timezone

logger = logging.getLogger("studio")


def apply_distribution_for_run(run_id) -> dict:
    """Apply the client's distribution rules to a finished PlayRun's outputs.

    Returns ``{"posts_created": n}``.
    """
    from . import models, services

    run = models.PlayRun.objects.filter(id=run_id).select_related("project", "project__client").first()
    if not run:
        logger.warning("apply_distribution_for_run: run %s not found", run_id)
        return {"posts_created": 0}

    project = run.project
    client = project.client

    # The variants this run produced (MediaAsset.play_run == run).
    variants = list(run.outputs.all())
    if not variants:
        return {"posts_created": 0}

    # Formats we actually produced -> the variant assets for each format.
    produced: dict[str, list] = {}
    for v in variants:
        produced.setdefault(v.format, []).append(v)

    rules = client.distribution_rules.filter(active=True)

    # Brand kit drives caption tone + default hashtags (may not exist).
    brandkit = getattr(client, "brand_kit", None)
    tone = getattr(brandkit, "tone_of_voice", "") or ""
    brand_hashtags = getattr(brandkit, "hashtags_csv", "") or ""

    # Idempotency: (platform, source_format) already posted from THIS run.
    handled: set[tuple[str, str]] = set()
    for pm in models.PostMedia.objects.filter(media__play_run=run).select_related("post", "media"):
        if pm.post:
            handled.add((pm.post.platform, pm.media.format))

    # Channels keyed by platform for quick lookup.
    accounts = {a.platform: a for a in client.social_accounts.all()}

    created = 0
    for rule in rules:
        matching = produced.get(rule.source_format)
        if not matching:
            continue  # this run produced nothing in the rule's source format

        for platform in rule.platforms:
            key = (platform, rule.source_format)
            if key in handled:
                continue  # already created for this run — idempotent skip

            account = accounts.get(platform)
            if not account:
                logger.info(
                    "distribution: %s has no %s channel; skipping rule %s",
                    client.name, platform, rule.id,
                )
                continue

            # Compose the caption via the AI/template service.
            cap = services.generate_caption(
                project.summary, platform, tone=tone, hashtags=brand_hashtags,
            )

            authorized = bool(account.connected and account.authorized_at)
            will_auto = bool(rule.auto_post and authorized)

            post = models.Post.objects.create(
                client=client,
                project=project,
                author=run.triggered_by,
                social_account=account,
                platform=platform,
                status=(models.Post.Status.SCHEDULED if will_auto else models.Post.Status.DRAFT),
                caption=cap.get("caption", ""),
                caption_ai=cap.get("caption", ""),
                hashtags=cap.get("hashtags", "")[:500],
                scheduled_at=(timezone.now() if will_auto else None),
            )

            # Attach every variant for this source format (position-ordered).
            for pos, asset in enumerate(matching):
                models.PostMedia.objects.get_or_create(
                    post=post, media=asset, defaults={"position": pos},
                )

            handled.add(key)
            created += 1

            if will_auto:
                # Enqueue the real publish (eager in dev, Celery in prod).
                try:
                    from .tasks import publish_post_task

                    publish_post_task.delay(post.id)
                    logger.info(
                        "auto-posting %s post %s for %s", platform, post.id, client.name,
                    )
                except Exception:  # never fail distribution because enqueue hiccuped
                    logger.exception("failed to enqueue publish for post %s", post.id)

    logger.info("distribution for run %s created %s posts", run.id, created)
    return {"posts_created": created}
