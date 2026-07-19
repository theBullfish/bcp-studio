# BCP Studio — Build Spec & Conventions

Read this before adding code. Follow it exactly so every module stays consistent
and compiles together.

## Stack
- Next.js 14 App Router, TypeScript, React server components by default.
- Tailwind (dark theme). Prisma + PostgreSQL. NextAuth (credentials).
- Python worker (FastAPI) for AI plays / media — the web app talks to it over HTTP.

## Directory conventions
- Pages: `web/src/app/(app)/<feature>/page.tsx` (+ `[id]/page.tsx` for detail).
- API: `web/src/app/api/<feature>/route.ts` (+ `[id]/route.ts`).
- Client components need `"use client"`. Server components are the default and may
  be `async` and query Prisma directly.
- Add `export const dynamic = "force-dynamic";` to any page/route that reads the DB.
- DO NOT modify: `prisma/schema.prisma`, `src/lib/*`, `src/components/Sidebar.tsx`,
  `src/components/ui.tsx`, `src/app/(app)/layout.tsx`, `src/app/globals.css`.
  Only ADD files in your assigned feature directories.

## Shared imports (already exist — use them, don't recreate)
```ts
import { prisma } from "@/lib/db";
import { requireUser, requireCapability, CAN, getSessionUser } from "@/lib/rbac";
import { PageHeader, StatCard, Badge, EmptyState } from "@/components/ui";
import { money, compactNumber, timeAgo, PLATFORM_META, STATUS_META } from "@/lib/format";
```
- `requireUser()` -> SessionUser {id,email,name,role} or redirects to /login.
- `requireCapability(CAN.approvePost)` etc. redirects to /unauthorized if not allowed.
- `CAN` has: manageUsers, manageClients, manageBilling, createProject, runPlays,
  editMedia, draftPost, schedulePost, approvePost, viewAnalytics, viewPay — each `(role)=>boolean`.
- UI: `<PageHeader title subtitle action/>`, `<StatCard label value hint tone/>`,
  `<Badge tone>`, `<EmptyState title hint cta={{href,label}}/>`.
- CSS classes available: `card`, `btn-primary`, `btn-ghost`, `input`, `label`, `pill`.

## API route style
```ts
import { NextResponse } from "next/server";
import { prisma } from "@/lib/db";
import { getSessionUser } from "@/lib/rbac";
export const dynamic = "force-dynamic";
export async function POST(req: Request) {
  const user = await getSessionUser();
  if (!user) return NextResponse.json({ error: "unauthorized" }, { status: 401 });
  const body = await req.json();
  // ...validate, write, return
  return NextResponse.json({ ok: true });
}
```
Mutations from client components: `fetch("/api/...", {method,body:JSON.stringify(...)})`
then `router.refresh()`.

## Worker client
`import { worker } from "@/lib/worker";` exposes `worker.runPlay(...)`, `worker.generateCaption(...)`.
It falls back to deterministic mock output if the worker is unreachable, so UI always works.

## Data model (see prisma/schema.prisma for the full truth)
Key models & important fields:
- User{id,email,name,role(Role),active,payRateCents}
- Role enum: OWNER>ADMIN>PRODUCER>EDITOR>APPROVER>CONTRIBUTOR>VIEWER
- Client{id,name,slug,active} has BrandKit(1:1), BrandAsset[], SocialAccount[], Project[], Post[], Release[], RevenueEntry[]
- BrandKit{clientId,primaryColor,secondaryColor,accentColor,fontHeading,fontBody,logoUrl,logoMarkUrl,watermarkUrl,toneOfVoice,hashtagsCsv}
- Project{id,clientId,ownerId,title,summary,status(ProjectStatus)} has MediaAsset[], PlayRun[], Post[]
- MediaAsset{id,projectId,kind(MediaKind),status,label,url,thumbnailUrl,durationMs,format,derivedFromId,playRunId}
- Play{id,key,name,description,steps(Json),outputs(Json),builtin,active} has PlayRun[]
- PlayRun{id,playId,projectId,triggeredById,status(PlayRunStatus),progress,error} has outputs MediaAsset[]
- SocialAccount{id,clientId,platform(Platform),handle,displayName,connected}
- Post{id,clientId,projectId?,authorId,socialAccountId?,platform,status(PostStatus),caption,captionAi,hashtags,scheduledAt,publishedAt,externalUrl} has PostMedia[], Approval[], PostMetric[]
- PostMedia{postId,mediaId,position}
- Approval{id,postId,reviewerId,decision(ApprovalDecision),comment,decidedAt}
- Release{id,clientId,projectId?,title,kind(ReleaseKind),releaseDate,isPrimary,notes}
- CalendarEvent{id,title,kind(CalendarEventKind),start,end?,allDay,clientId?,notes}
- PostMetric{postId,capturedAt,impressions,reach,likes,comments,shares,saves,views,clicks,revenueCents}
- RevenueEntry{id,clientId,source(RevenueSource),amountCents,currency,occurredAt,note}
- PayEntry{id,userId,amountCents,currency,periodStart,periodEnd,note,paid}
- TrendItem{id,source,title,url,score,category,capturedAt}
- Conversation{id,title} + ConversationParticipant{conversationId,userId,lastReadAt} + Message{conversationId,senderId,body}
- Notification{userId,kind,title,body,link,read}
- AuditLog{userId?,action,entity,entityId,meta}

Enums:
- ProjectStatus: DRAFT|PROCESSING|READY|SCHEDULED|ARCHIVED
- MediaKind: VIDEO|AUDIO|IMAGE|DOCUMENT ; MediaStatus: UPLOADING|UPLOADED|PROCESSING|READY|FAILED
- PlayRunStatus: QUEUED|RUNNING|SUCCEEDED|FAILED|CANCELLED
- Platform: INSTAGRAM|TIKTOK|YOUTUBE|X|FACEBOOK|LINKEDIN|THREADS
- PostStatus: DRAFT|IN_REVIEW|APPROVED|SCHEDULED|PUBLISHING|PUBLISHED|FAILED|REJECTED
- ApprovalDecision: PENDING|APPROVED|REJECTED|CHANGES_REQUESTED
- ReleaseKind: SINGLE|ALBUM|EP|VIDEO|EPISODE|CAMPAIGN|EVENT|OTHER
- CalendarEventKind: RELEASE|MEETING|DEADLINE|SHOOT|HOLD|OTHER
- RevenueSource: STREAMING|SYNC|MERCH|AD_REVENUE|SPONSORSHIP|LIVE|OTHER

## Privacy rule
All analytics/metrics/revenue/pay are INTERNAL only. Never expose them on public/unauthenticated
routes. Everything under (app)/ and /api/ requires a session.
