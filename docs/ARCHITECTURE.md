# Architecture

## Shape

```
                    ┌──────────────────────────────────────────┐
  Browser  ───────► │  web/  Next.js 14 (App Router)            │
                    │   • React server components (UI)          │
                    │   • /api route handlers (mutations)       │
                    │   • NextAuth (credentials, JWT session)   │
                    │   • Prisma client                         │
                    └───────┬──────────────────────┬───────────┘
                            │                       │
                     Prisma │                       │ HTTP
                            ▼                       ▼
                    ┌───────────────┐      ┌────────────────────────┐
                    │ PostgreSQL 16 │      │ worker/ FastAPI (Python)│
                    │  (all data)   │      │  • AI plays (ffmpeg)    │
                    └───────────────┘      │  • caption gen (Claude) │
                                           └────────────────────────┘
```

## Why this split

- **Next.js owns everything user-facing** — pages, auth, CRUD API, the calendar, the
  dashboards. One TypeScript codebase, one deploy target (Vercel or the bundled Docker image).
- **Python worker owns the heavy/AI work** — media decomposition with ffmpeg and caption
  generation with the Claude API. This is where the "record a bit, get every format" magic
  runs, and it's the piece most likely to grow (GPU jobs, transcription, real editing).
- The web app calls the worker through `web/src/lib/worker.ts`, which **degrades gracefully**:
  if the worker is unreachable it returns deterministic mock output, so the product is always
  demoable and the two services can be developed independently.

## Data model

`web/prisma/schema.prisma` is the single source of truth. Domains:

- **Identity**: `User`, `Session`, `Role`, `ClientMembership`.
- **Brands**: `Client`, `BrandKit`, `BrandAsset`, `SocialAccount`.
- **Content**: `Project`, `MediaAsset` (source + derived variants), `Play`, `PlayRun`.
- **Publishing**: `Post`, `PostMedia`, `Approval`.
- **Calendar**: `Release`, `CalendarEvent`.
- **Tracking (private)**: `PostMetric`, `RevenueEntry`, `PayEntry`, `TrendItem`.
- **Comms**: `Conversation`, `ConversationParticipant`, `Message`, `Notification`, `AuditLog`.

## The production loop, mapped to code

1. **Record a bit** → `Project` + source `MediaAsset` (Projects module).
2. **Hand it to the server** → trigger a `Play` → `PlayRun` (POST `/api/plays/run`) →
   worker decomposes → derived `MediaAsset` rows (`derivedFromId`, `playRunId`).
3. **Quick-finish** → Editor module edits the derived variant / draft.
4. **Auto-copy** → `worker.generateCaption()` fills `Post.caption` from `Project.summary`,
   brand-tone-aware.
5. **Approve** → `Approval` rows; `APPROVER`+ decide; on approval the post becomes `SCHEDULED`.
6. **Auto-post** → scheduler publishes at `scheduledAt` via the platform provider, writes
   `externalUrl`, then polls `PostMetric` (private analytics).

## Security / privacy

- Everything under `(app)/` and `/api/` requires a session.
- Analytics, revenue and pay are internal-only and never rendered on a public route.
- RBAC is centralized in `web/src/lib/rbac.ts`. Social tokens are stored server-side
  (encrypt at rest in production).

## Roadmap-level integration points (stubbed, pluggable)

- **Object storage** for real media (S3/R2) — `MediaAsset.storageKey`.
- **Platform providers** — real OAuth + publish per `Platform`; the schema and post
  lifecycle already model it end to end.
- **Transcription / highlight detection** in the worker (whisper + scene detection).
- **Scheduler** — a cron/queue that publishes due posts and pulls metrics.
