# Roadmap

Honest status. "Done" means built and wired; "Stub" means modeled with a graceful
fallback but not connected to a real external service yet.

## Phase 1 — Foundation & end-to-end slice  ✅ done
- [x] Full data model (Prisma) covering every domain
- [x] Auth (NextAuth credentials), JWT sessions
- [x] Role-based access control (7 roles, capability matrix)
- [x] App shell: sidebar nav, layout, dark theme
- [x] Control Room dashboard (congregated tracking view)
- [x] Python worker: AI plays engine + caption generation (Claude-ready)
- [x] Seed data: 6 users, 3 clients w/ brand kits, plays, projects, posts, metrics, revenue
- [x] Docker compose (db + web + worker)

## Phase 2 — Feature modules  ✅ done (first pass)
- [x] Clients &amp; Brand Kits (logos, colors, fonts, voice, social accounts)
- [x] Projects &amp; Media (upload, source + derived variants)
- [x] AI Plays (browse, trigger a run, see generated variants)
- [x] Posts &amp; Schedule (compose, auto-caption, schedule)
- [x] Calendar (my-release-dates view + company view)
- [x] Approvals (review queue, approve/reject/request changes)
- [x] Analytics (revenue, performance, pay — private)
- [x] Messaging (conversations)
- [x] Team (users, roles)

## Phase 3 — Make it real  ⏳ next
- [ ] Object storage for media (S3/R2) + real upload pipeline
- [ ] Worker: transcription (whisper) + highlight/scene detection for smarter cuts
- [ ] Real quick-finish editor (trim/caption/brand overlay in-browser)
- [ ] Platform providers: OAuth + publish for Instagram, TikTok, YouTube, X
- [ ] Scheduler service: publish due posts, poll live metrics
- [ ] Trends ingestion (Google Trends / RSS) on a schedule

## Phase 4 — Scale &amp; polish
- [ ] Notifications (email/push) + realtime messaging
- [ ] Stripe billing per client / usage
- [ ] Audit log UI, granular per-client roles
- [ ] Mobile-friendly capture ("record a bit" from your phone)
