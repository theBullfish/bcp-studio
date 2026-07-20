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

## Phase 3 — Make it real  ⏳ next
- [ ] Object storage for media (S3/R2) + real upload pipeline
- [ ] Worker: transcription (whisper) + highlight/scene detection for smarter cuts
- [ ] In-browser quick-finish editor (trim / caption / brand overlay)
- [ ] Platform providers: OAuth + publish for Instagram, TikTok, YouTube, X
- [ ] Celery + beat: publish due posts, poll live metrics, ingest trends
- [ ] Notifications (email/push), realtime messaging

## Phase 4 — Scale &amp; polish
- [ ] Stripe billing per client / usage
- [ ] Granular per-client roles, audit-log UI
- [ ] Mobile capture ("record a bit" from your phone)
