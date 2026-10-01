# STATUS — Balls & Chunk Studio

*Verified 2026-10-01 by install → migrate → test → boot on a clean checkout, not from the roadmap's self-assessment. This is the honest state.*

## Verdict

A **solid first-pass product that runs**, further along than most things called "done."
It is **not yet battle-tested**: no code path has touched a live social platform, and the
async worker is wired but not deployed. The gap from here to "I posted to a client's
Instagram from this" is roughly a day of OAuth-app setup plus one worker deployment —
not a rebuild.

## What was actually verified (clean checkout, SQLite)

- `pip install -r requirements.txt` — clean.
- `python manage.py migrate` — all migrations apply (studio 0001 + 0002).
- `python -m pytest` — **50 tests pass** (36 test functions across 7 files:
  models 11, rbac 7, plays 4, ingest 4, video-access 4, store 3, pages 3).
- `python manage.py seed_studio` — seeds 6 users, 3 clients with brand kits, plays,
  projects, posts, metrics, revenue, distribution, a capture device.
- `python manage.py runserver` — boots; `/` redirects to auth (302) as intended.

## What is real (not stubbed)

- **Per-platform publishers** (`studio/publishers/{instagram,x,tiktok,youtube}.py`) make
  real POST calls to the actual endpoints — Graph v19 two-step (`/media` →
  `/media_publish`), X v1.1 media upload + tweet, TikTok, YouTube multipart upload.
  A `mock.py` publisher exists for tests; the real ones are real.
- **OAuth connect/callback** flow for linking client accounts (`views_publish.py`).
- **7-role RBAC** enforced in `models.py` (`role_at_least`) and checked in views.
- **Stripe store** — Product/Price/Order, hosted Checkout (reuses the GritBox account),
  webhook fulfillment, public storefront.
- **Paid video** — channels/videos/tiers, membership subs, access-gated self-hosted HLS.
- **Capture → sync** — Device model, key-authed `/ingest/` API, `syncagent/agent.py`
  (watches a folder, resumable upload over Tailscale).
- **AI captions** — Claude-powered when `ANTHROPIC_API_KEY` is set, deterministic
  template fallback otherwise.

## The three asterisks on "solid"

1. **No live-platform run.** The publisher API code is correct against the docs but has
   never run against real Instagram / X / TikTok / YouTube credentials. Real OAuth apps
   carry review processes, scope approvals, and undocumented quirks. First real post is
   where those surface. **This is the one load-bearing unknown.**
2. **Async layer not deployed.** AI plays (ffmpeg transcode) and auto-post are
   Celery-ready but there is no evidence of a running worker + broker. Inline execution
   will block the web request on a large source. Stand up a worker before real use.
3. **Tests cover our own logic, not the external posts.** 50 green means the plumbing is
   sound (RBAC, models, store, ingest, pages) — it does **not** mean a post has ever
   landed on a timeline, because those calls are mocked in tests.

## First real step (if taken to production)

A one-command smoke test: connect one real platform account, push one post through the
real publisher, confirm it lands. That single run retires asterisk #1 and tells you more
than any amount of additional unit testing.

## Environment hookups required for production

- `ANTHROPIC_API_KEY` — live captions (else templates).
- Per-platform OAuth app credentials (client id/secret, approved scopes, redirect URIs).
- Stripe keys + webhook secret (store).
- PostgreSQL (prod; SQLite is dev-only).
- Celery broker (Redis) + worker for plays/auto-post.
- Tailscale for the capture agent's ingest path.
