# BCP Studio — CLAUDE.md

## What this is
AI media production & social publishing platform for Balls and Chunk Productions.
Record a bit → AI plays cut it into every format → finish → approve → auto-post → track.

## Layout
- `web/` — Next.js 14 (App Router, TS, Tailwind, Prisma, NextAuth). UI + API.
- `worker/` — Python/FastAPI. AI plays (ffmpeg) + caption generation (Claude).
- `web/prisma/schema.prisma` — the single source of truth for data.
- `docs/BUILD_SPEC.md` — conventions. Read before adding code.
- `docs/ARCHITECTURE.md`, `ROADMAP.md` — design + status.

## Conventions
- Server components by default; `"use client"` only when needed.
- Add `export const dynamic = "force-dynamic";` to DB-reading pages/routes.
- Shared code lives in `web/src/lib/*` and `web/src/components/*` — reuse, don't duplicate.
- RBAC via `web/src/lib/rbac.ts` (`CAN`). Worker calls via `web/src/lib/worker.ts`.
- Analytics/revenue/pay are INTERNAL only — never on a public route.

## Commands
```bash
docker compose up --build          # full stack
cd web && npm run dev               # web only (needs DATABASE_URL + a running db)
cd web && npm run db:push && npm run db:seed
cd worker && uvicorn app.main:app --reload --port 8800
cd worker && pytest
```

## Login (seed)
owner@ballsandchunk.com / chunk1234
