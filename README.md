# Balls &amp; Chunk Studio

An AI media production &amp; social publishing platform for **Balls and Chunk Productions**
(and resellable per-client). The core loop:

> **Record a bit → hand it to the server → AI "plays" cut it into every format you need →
> a person quickly finishes the edit → approvers sign off → it auto-posts on schedule,
> with all the tracking data attached.**

## What's in the box

- **AI Plays** — pre-built recipes that decompose one source into every deliverable
  (vertical reels, squares, stories, audiograms, quote cards, thumbnails, transcripts…).
- **Quick-finish editor** — polish an AI cut before it ships.
- **Auto-copy** — captions written from your one-line summary (Claude-powered when a key
  is set, deterministic templates otherwise), brand-tone aware.
- **Clients / brands** — each client has its own logos, colors, fonts and voice, applied
  automatically to their content.
- **Scheduling &amp; posting** — manual or automatic, per platform, on a calendar.
- **Two calendar views** — a focused *your release dates* view and a company-wide view.
- **Approvals** — multi-level roles; a couple of people sign off before anything posts.
- **Private tracking** — revenue, pay, post performance, trends/news — internal only,
  never exposed to the outside world.
- **Accounts &amp; messaging** — profiles, roles, in-app messaging, notifications.

## Architecture

Monorepo, two services (see `docs/ARCHITECTURE.md`):

- `web/` — **Next.js 14** (App Router, TypeScript, Tailwind, Prisma, NextAuth). UI + API.
- `worker/` — **Python / FastAPI**. Runs the AI plays (ffmpeg media decomposition) and
  caption generation. The web app talks to it over HTTP and degrades gracefully if it's down.
- **PostgreSQL** for everything. **Prisma** owns the schema (`web/prisma/schema.prisma`).

## Quick start (Docker)

```bash
cp .env.example .env          # set NEXTAUTH_SECRET; add ANTHROPIC_API_KEY for real captions
docker compose up --build
# web:    http://localhost:3000
# worker: http://localhost:8800/health
```

The web container pushes the schema and seeds demo data on first boot.

**Login:** `owner@ballsandchunk.com` / `chunk1234` (six seeded users, one per role).

## Local dev (without Docker)

```bash
# 1. Postgres
docker compose up -d db

# 2. Web
cd web
npm install
export DATABASE_URL=postgresql://bcp:bcp@localhost:5432/bcp_studio
npm run db:push && npm run db:seed
npm run dev            # http://localhost:3000

# 3. Worker (separate shell)
cd worker
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8800
```

## Roles

`OWNER → ADMIN → PRODUCER → EDITOR → APPROVER → CONTRIBUTOR → VIEWER`
Capabilities are enforced in `web/src/lib/rbac.ts` (`CAN`).

## Status

This is the first end-to-end slice: full data model, auth, all core screens, the plays
worker, and seeded demo data. See `ROADMAP.md` for what's built and what's next.
