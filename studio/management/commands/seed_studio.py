"""Seed BCP Studio with a realistic demo dataset.

Idempotent-ish: safe to re-run; it upserts users/clients/plays and tops up
projects/posts/metrics. Creates the login accounts (one per role).

    python manage.py seed_studio
"""

import random
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.utils import timezone

from studio import models


class Command(BaseCommand):
    help = "Seed demo data for BCP Studio"

    def handle(self, *args, **opts):
        random.seed(42)
        now = timezone.now()

        # ---- Users (one per role) --------------------------------------
        people = [
            ("owner", "owner@ballsandchunk.com", "Brad Svenson", "OWNER", 0),
            ("dana", "admin@ballsandchunk.com", "Dana Ruiz", "ADMIN", 6500),
            ("marcus", "producer@ballsandchunk.com", "Marcus Lee", "PRODUCER", 5500),
            ("priya", "editor@ballsandchunk.com", "Priya Shah", "EDITOR", 4500),
            ("toni", "approver@ballsandchunk.com", "Toni Blake", "APPROVER", 5000),
            ("sam", "contrib@ballsandchunk.com", "Sam Ortiz", "CONTRIBUTOR", 3500),
        ]
        users = {}
        for username, email, name, role, pay in people:
            u, created = User.objects.get_or_create(
                username=username, defaults={"email": email}
            )
            first, _, last = name.partition(" ")
            u.email = email
            u.first_name, u.last_name = first, last
            u.is_staff = role in ("OWNER", "ADMIN")
            u.is_superuser = role == "OWNER"
            u.set_password("chunk1234")
            u.save()
            prof = u.profile
            prof.role = role
            prof.pay_rate_cents = pay
            prof.title = role.title()
            prof.save()
            users[username] = u
        self.stdout.write("  users ✓")

        # ---- Clients + brand kits + socials ----------------------------
        client_defs = [
            ("Balls & Chunk Productions", "balls-and-chunk", "#6d28d9", "#f59e0b",
             "Raw, funny, hip-hop energy. Punchy. Never corporate."),
            ("Neon Alley Records", "neon-alley", "#0ea5e9", "#ec4899",
             "Slick, nightlife, synthwave. Confident and cool."),
            ("Deep Cut Podcast Network", "deep-cut", "#10b981", "#f43f5e",
             "Thoughtful, curious, conversational. Smart but warm."),
        ]
        platforms = ["INSTAGRAM", "TIKTOK", "YOUTUBE", "X"]
        clients = []
        for name, slug, primary, accent, tone in client_defs:
            c, _ = models.Client.objects.get_or_create(slug=slug, defaults={"name": name})
            kit, _ = models.BrandKit.objects.get_or_create(client=c)
            kit.primary_color = primary
            kit.accent_color = accent
            kit.tone_of_voice = tone
            kit.hashtags_csv = "#newmusic,#indie,#nowplaying"
            kit.save()
            for plat in platforms:
                models.SocialAccount.objects.get_or_create(
                    client=c, platform=plat, handle=f"@{slug}",
                    defaults={"connected": plat != "X"},
                )
            for u in users.values():
                models.ClientMembership.objects.get_or_create(user=u, client=c)
            clients.append(c)
        self.stdout.write("  clients ✓")

        # ---- Builtin plays ---------------------------------------------
        plays = [
            ("shorts_pack", "Shorts Pack",
             "Turn one long video into 3 vertical reels, a square teaser, and a thumbnail.",
             [{"op": "transcribe"}, {"op": "detect_highlights", "count": 3},
              {"op": "cut", "format": "reel_9x16", "count": 3, "captions": True},
              {"op": "cut", "format": "square_1x1", "count": 1},
              {"op": "still", "format": "still_thumb"}, {"op": "brand_overlay"}],
             ["reel_9x16", "square_1x1", "still_thumb"]),
            ("podcast_clips", "Podcast Clips",
             "Audiograms, quote cards, and a transcript from an episode.",
             [{"op": "transcribe"}, {"op": "detect_quotes", "count": 2},
              {"op": "audiogram", "format": "audiogram_1x1", "count": 2},
              {"op": "quote_card"}, {"op": "export_transcript"}],
             ["audiogram_1x1", "quote_card", "transcript"]),
            ("release_kit", "Release Kit",
             "Full announcement kit for a new single or album drop.",
             [{"op": "cover_from_art"}, {"op": "cut", "format": "reel_9x16", "count": 1},
              {"op": "story", "format": "story_9x16"}, {"op": "banner", "format": "banner_16x9"},
              {"op": "brand_overlay"}],
             ["reel_9x16", "square_1x1", "story_9x16", "banner_16x9"]),
        ]
        for key, name, desc, steps, outs in plays:
            models.Play.objects.update_or_create(
                key=key,
                defaults={"name": name, "description": desc, "steps": steps,
                          "outputs": outs, "builtin": True, "active": True},
            )
        self.stdout.write("  plays ✓")

        # ---- Projects, media, posts, metrics ---------------------------
        if models.Project.objects.count() == 0:
            titles = [
                "Midnight Freestyle Session", "Studio Vlog — Ep. 12",
                "New Single: 'Gravel'", "Deep Cut #48: The Sample Debate",
                "Rooftop Live Set",
            ]
            caps = [
                "Behind the boards on the new one. This beat almost didn't make it 😅",
                "3AM in the booth hits different. Full track drops Friday 🔥",
                "You asked, we delivered. 'Gravel' is out everywhere now.",
                "Hot take: the sample makes the song. Fight us in the comments.",
                "Rooftop set was unreal. Swipe for the full moment.",
            ]
            for i, title in enumerate(titles):
                client = clients[i % len(clients)]
                proj = models.Project.objects.create(
                    client=client, owner=random.choice([users["owner"], users["marcus"]]),
                    title=title, summary=caps[i],
                    status=random.choice(["READY", "SCHEDULED", "PROCESSING"]),
                )
                src = models.MediaAsset.objects.create(
                    project=proj, kind="VIDEO", status="READY", label="Source recording",
                    url="https://example.com/source.mp4", duration_ms=random.randint(60000, 900000),
                    uploader=users["marcus"],
                )
                models.MediaAsset.objects.create(
                    project=proj, kind="VIDEO", status="READY", label="Vertical Reel #1",
                    format="reel_9x16", url="https://example.com/reel1.mp4", derived_from=src,
                )
                for _ in range(random.randint(1, 2)):
                    plat = random.choice(platforms)
                    acct = models.SocialAccount.objects.filter(client=client, platform=plat).first()
                    status = random.choice(["PUBLISHED", "SCHEDULED", "IN_REVIEW", "DRAFT"])
                    post = models.Post.objects.create(
                        client=client, project=proj,
                        author=random.choice([users["marcus"], users["owner"]]),
                        social_account=acct, platform=plat, status=status,
                        caption=caps[i], caption_ai=caps[i],
                        hashtags="#ballsandchunk #newmusic #studio",
                        scheduled_at=now + timedelta(days=random.randint(1, 21)) if status == "SCHEDULED" else None,
                        published_at=now - timedelta(days=random.randint(1, 30)) if status == "PUBLISHED" else None,
                        external_url="https://instagram.com/p/demo" if status == "PUBLISHED" else "",
                    )
                    if status == "IN_REVIEW":
                        models.Approval.objects.get_or_create(post=post, reviewer=users["toni"])
                    if status == "PUBLISHED":
                        models.PostMetric.objects.create(
                            post=post, impressions=random.randint(2000, 90000),
                            reach=random.randint(1500, 70000), likes=random.randint(100, 6000),
                            comments=random.randint(5, 400), shares=random.randint(2, 800),
                            saves=random.randint(10, 1200), views=random.randint(3000, 150000),
                            clicks=random.randint(20, 900), revenue_cents=random.randint(0, 40000),
                        )
                if i % 2 == 0:
                    models.Release.objects.create(
                        client=client, project=proj, title=title,
                        kind=random.choice(["SINGLE", "VIDEO", "EPISODE", "ALBUM"]),
                        release_date=now + timedelta(days=random.randint(-10, 28)),
                        is_primary=(client.slug == "balls-and-chunk"),
                    )
            self.stdout.write("  projects/posts ✓")

        # ---- Revenue ----------------------------------------------------
        if models.RevenueEntry.objects.count() == 0:
            for client in clients:
                for m in range(6):
                    models.RevenueEntry.objects.create(
                        client=client,
                        source=random.choice(["STREAMING", "MERCH", "SYNC", "AD_REVENUE", "SPONSORSHIP"]),
                        amount_cents=random.randint(20000, 350000),
                        occurred_at=now - timedelta(days=m * 30 + random.randint(0, 20)),
                    )
            for u in users.values():
                rate = u.profile.pay_rate_cents or 0
                if rate:
                    models.PayEntry.objects.create(
                        user=u, amount_cents=rate * random.randint(20, 80),
                        period_start=now - timedelta(days=14), period_end=now,
                    )
            self.stdout.write("  revenue/pay ✓")

        # ---- Trends -----------------------------------------------------
        if models.TrendItem.objects.count() == 0:
            for source, title, cat in [
                ("google-trends", "Indie hip-hop streams up 24% this quarter", "industry"),
                ("rss:pitchfork", "The return of the physical single", "news"),
                ("tiktok-sounds", "Slowed + reverb trend resurging", "trend"),
                ("google-trends", "'Type beat' searches spike on weekends", "trend"),
                ("rss:billboard", "Short-form video now drives 60% of discovery", "news"),
            ]:
                models.TrendItem.objects.create(
                    source=source, title=title, category=cat,
                    url="https://example.com", score=random.random(),
                )

        # ---- Company calendar events -----------------------------------
        if models.CalendarEvent.objects.count() == 0:
            for title, kind, day in [
                ("Weekly release sync", "MEETING", 2),
                ("Master due — 'Gravel'", "DEADLINE", 5),
                ("Rooftop shoot", "SHOOT", 9),
                ("Studio hold", "HOLD", 14),
            ]:
                models.CalendarEvent.objects.create(
                    title=title, kind=kind, start=now + timedelta(days=day),
                    end=now + timedelta(days=day, hours=2),
                )

        # ---- A demo conversation ---------------------------------------
        if models.Conversation.objects.count() == 0:
            convo = models.Conversation.objects.create(title="Friday drop plan")
            convo.participants.set([users["owner"], users["marcus"], users["toni"]])
            for sender, body in [
                (users["marcus"], "Reels for 'Gravel' are cut and in review 🎬"),
                (users["toni"], "Looking now — approving the first two."),
                (users["owner"], "🔥 ship it Friday 9am like usual"),
            ]:
                models.Message.objects.create(conversation=convo, sender=sender, body=body)

        # ---- Store: products + prices ----------------------------------
        if models.Product.objects.count() == 0:
            catalog = [
                ("Gravel — Limited Vinyl", "PHYSICAL", 3200),
                ("Studio Hoodie", "PHYSICAL", 5500),
                ("'Gravel' Digital Single", "DIGITAL", 199),
                ("Rooftop Live — Ticket", "TICKET", 2500),
            ]
            for i, (name, kind, cents) in enumerate(catalog):
                client = clients[i % len(clients)]
                prod = models.Product.objects.create(
                    client=client, name=name, slug=f"{client.slug}-{i}",
                    kind=kind, description="Official Balls & Chunk merch.",
                    image_url="", active=True,
                )
                models.Price.objects.create(product=prod, unit_amount_cents=cents, active=True)
            self.stdout.write("  store ✓")

        # ---- Paid video: channel + plans + videos ----------------------
        if models.Channel.objects.count() == 0:
            bc = clients[0]
            channel = models.Channel.objects.create(
                client=bc, name="Balls & Chunk TV", slug="bc-tv",
                description="Behind the scenes, full sessions, and members-only cuts.",
            )
            models.MembershipPlan.objects.create(
                channel=channel, name="Supporter", tier=1, amount_cents=500, interval="month",
                perks="Members-only videos, early access.",
            )
            models.MembershipPlan.objects.create(
                channel=channel, name="Backstage", tier=2, amount_cents=1500, interval="month",
                perks="Everything in Supporter + full unedited sessions + monthly hangout.",
            )
            for i, (title, vis) in enumerate([
                ("Studio Vlog — Ep. 12 (Free)", "PUBLIC"),
                ("Full Session: 'Gravel' (Members)", "MEMBERS"),
                ("Backstage: Rooftop Rehearsal (Tier 2)", "TIER"),
            ]):
                models.Video.objects.create(
                    channel=channel, title=title, slug=f"v{i}",
                    description="Self-hosted on the BC servers.",
                    source_url="https://example.com/demo.mp4",
                    visibility=vis, min_tier=2 if vis == "TIER" else 1,
                    status="READY", published_at=now - timedelta(days=i),
                )
            self.stdout.write("  video platform ✓")

        # ---- Distribution rules + platform profiles --------------------
        if models.DistributionRule.objects.count() == 0:
            for client in clients:
                models.DistributionRule.objects.create(
                    client=client, source_format="reel_9x16",
                    platforms=["INSTAGRAM", "TIKTOK", "YOUTUBE"], auto_post=True, active=True)
                models.DistributionRule.objects.create(
                    client=client, source_format="square_1x1",
                    platforms=["INSTAGRAM", "FACEBOOK"], auto_post=False, active=True)
                for plat in ["INSTAGRAM", "TIKTOK"]:
                    models.PlatformProfile.objects.get_or_create(
                        client=client, platform=plat,
                        defaults={"posting_cadence": "3x/week", "best_times": "9am, 6pm",
                                  "default_hashtags": "#ballsandchunk #newmusic"})
            self.stdout.write("  distribution ✓")

        # ---- Capture device (Tailscale sync) ---------------------------
        if models.Device.objects.count() == 0:
            models.Device.objects.create(
                name="Brad's MacBook (field)", client=clients[0],
                target_project=models.Project.objects.first(),
                tailnet_host="temple.tailnet.ts.net", auto_run_play="shorts_pack",
            )
            self.stdout.write("  capture device ✓")

        self.stdout.write(self.style.SUCCESS("Seed complete."))
        self.stdout.write("Login: owner@ballsandchunk.com / chunk1234 (or username 'owner')")
