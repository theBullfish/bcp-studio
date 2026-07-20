# Roadmap

Honest status. "Done" = built and wired. "Stub" = modeled with a graceful fallback
but not connected to a real external service yet.

## Phase 1 — Foundation on Skote  ✅ done
- [x] Skote Django template adopted as the base (real components, not reskinned)
- [x] Full data model (`studio/models.py`) covering every domain
- [x] Auth via allauth + 7-role RBAC (Owner→…→Viewer)
- [x] Django admin registered for every model (back office)
- [x] Custom sidebar nav + branding
- [x] AI plays engine + caption generation in `studio/services.py` (ffmpeg + Claude-ready)
- [x] Seed command: 6 users, 3 clients w/ brand kits, plays, projects, posts, metrics, revenue
- [x] Runs on SQLite with zero config

## Phase 2 — Screens (through Skote components)  ✅ done (first pass)
- [x] Control Room dashboard (ApexCharts revenue, stat cards, recent posts, releases, trends)
- [x] Clients &amp; Brand kits (colors/fonts/voice, channels)
- [x] Projects &amp; Media (source + derived variants, run a play)
- [x] AI Plays (browse recipes)
- [x] Posts &amp; Schedule (DataTable, compose w/ AI caption, detail)
- [x] Approvals queue (approve / request changes / reject)
- [x] Calendar (FullCalendar — my-release-dates + company views)
- [x] Analytics (ApexCharts revenue + by-source, top posts, private payroll)
- [x] Messaging (chat UI) + Team (roles)

## Phase 3 — The five pillars  ✅ done (first pass — see docs/PILLARS.md)
- [x] **Capture → sync (Tailscale)**: Device model + key-authed `/ingest/` API +
      `syncagent/agent.py` (watches a folder, resumable upload over the tailnet,
      files land as MediaAssets on a project)
- [x] **Socials & distribution**: per-client channels, distribution rules
      (format → platforms), per-platform profiles
- [x] **Client-as-tenant + authorize the app**: client types + per-channel
      authorization (who/when) + auto-post toggle
- [x] **Store (Stripe)**: Product/Price/Order + hosted Checkout (reuses GritBox
      account) + webhook fulfillment + public storefront
- [x] **Paid video platform**: Channels/Videos/tiers, membership subscriptions,
      access-gated self-hosted HLS (ffmpeg transcode + hls.js player)

## Phase 4 — Production-grade  ✅ done (first pass)
- [x] **Background jobs**: Celery app + tasks (plays, transcode, publish) + beat
      scheduler (publish due posts, poll metrics); eager fallback so dev needs no broker
- [x] **Real publishing pipeline**: per-platform providers (Instagram/TikTok/YouTube/X)
      with real API call structures, mock fallback, OAuth connect/callback flow
- [x] **Auto-post engine**: play outputs fan out to channels via DistributionRules
      (auto-post → schedule + publish; else draft)
- [x] **Object storage**: env-gated S3/R2 via django-storages; storage-backed uploads;
      signed/expiring HLS playback URLs (token-gated `hls_stream`)
- [x] **Quick-finish editor**: in-browser trim + caption → ffmpeg render task → derived asset
- [x] **Security hardening**: HSTS/SSL redirect/secure cookies (auto when DEBUG off),
      CSRF trusted origins, WhiteNoise static, structured logging, upload limits
- [x] **CI + tests**: GitHub Actions (ruff + check + migrations + pytest); 50-test suite
- [x] **Deploy**: docker-compose (db + redis + web + worker + beat), Makefile, deploy guide

## Phase 5 — Scale & depth  ⏳ next
- [ ] Live platform app registrations + token refresh; publish retries/backoff dashboards
- [ ] CDN in front of HLS; multi-bitrate ladder; whisper transcription + smarter highlights
- [ ] Stripe subscription lifecycle webhooks (renew/cancel/dunning) + customer portal
- [ ] Notifications (email/push), realtime messaging (channels/websockets)
- [ ] Per-client granular roles, audit-log UI, mobile capture app

## Phase 4 — Scale &amp; polish
- [ ] Stripe billing per client / usage
- [ ] Granular per-client roles, audit-log UI
- [ ] Mobile capture ("record a bit" from your phone)
