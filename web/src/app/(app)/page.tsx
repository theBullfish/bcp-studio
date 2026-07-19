import Link from "next/link";
import { prisma } from "@/lib/db";
import { requireUser } from "@/lib/rbac";
import { PageHeader, StatCard, Badge } from "@/components/ui";
import { money, compactNumber, timeAgo, PLATFORM_META, STATUS_META } from "@/lib/format";

export const dynamic = "force-dynamic";

export default async function ControlRoom() {
  const user = await requireUser();

  const now = new Date();
  const in30 = new Date(now.getTime() + 30 * 864e5);

  const [
    projectCount,
    scheduledCount,
    pendingApprovals,
    revenueAgg,
    recentPosts,
    upcomingReleases,
    trends,
    metricAgg,
  ] = await Promise.all([
    prisma.project.count({ where: { status: { not: "ARCHIVED" } } }),
    prisma.post.count({ where: { status: "SCHEDULED" } }),
    prisma.approval.count({ where: { decision: "PENDING" } }),
    prisma.revenueEntry.aggregate({ _sum: { amountCents: true } }),
    prisma.post.findMany({
      take: 6,
      orderBy: { updatedAt: "desc" },
      include: { client: true },
    }),
    prisma.release.findMany({
      where: { releaseDate: { gte: now, lte: in30 } },
      orderBy: { releaseDate: "asc" },
      take: 6,
      include: { client: true },
    }),
    prisma.trendItem.findMany({ orderBy: { capturedAt: "desc" }, take: 6 }),
    prisma.postMetric.aggregate({
      _sum: { impressions: true, views: true, likes: true },
    }),
  ]);

  return (
    <div>
      <PageHeader
        title={`Welcome back, ${user.name?.split(" ")[0] ?? "there"}`}
        subtitle="Everything the studio is doing, in one view."
      />

      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Revenue (all time)" value={money(revenueAgg._sum.amountCents ?? 0)} tone="emerald" />
        <StatCard label="Active projects" value={projectCount} tone="brand" />
        <StatCard label="Scheduled posts" value={scheduledCount} tone="sky" />
        <StatCard
          label="Awaiting approval"
          value={pendingApprovals}
          tone={pendingApprovals > 0 ? "amber" : "brand"}
        />
      </div>

      <div className="mt-4 grid grid-cols-2 gap-4 md:grid-cols-4">
        <StatCard label="Impressions" value={compactNumber(metricAgg._sum.impressions ?? 0)} />
        <StatCard label="Views" value={compactNumber(metricAgg._sum.views ?? 0)} />
        <StatCard label="Likes" value={compactNumber(metricAgg._sum.likes ?? 0)} />
        <StatCard label="Upcoming releases" value={upcomingReleases.length} tone="violet" />
      </div>

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        {/* Recent activity */}
        <div className="card p-5 lg:col-span-2">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold text-white">Recent posts</h2>
            <Link href="/posts" className="text-sm text-brand-400 hover:underline">
              View all
            </Link>
          </div>
          <div className="divide-y divide-white/5">
            {recentPosts.length === 0 && (
              <p className="py-6 text-sm text-zinc-500">No posts yet.</p>
            )}
            {recentPosts.map((p) => {
              const meta = STATUS_META[p.status] ?? { label: p.status, tone: "zinc" };
              return (
                <Link
                  key={p.id}
                  href={`/posts/${p.id}`}
                  className="flex items-center gap-3 py-3 hover:opacity-80"
                >
                  <span
                    className="h-2 w-2 shrink-0 rounded-full"
                    style={{ background: PLATFORM_META[p.platform]?.color }}
                  />
                  <span className="flex-1 truncate text-sm text-zinc-200">
                    {p.caption.slice(0, 70) || "(no caption)"}
                  </span>
                  <span className="hidden text-xs text-zinc-500 sm:block">
                    {p.client.name}
                  </span>
                  <Badge tone={meta.tone}>{meta.label}</Badge>
                  <span className="w-16 text-right text-xs text-zinc-600">
                    {timeAgo(p.updatedAt)}
                  </span>
                </Link>
              );
            })}
          </div>
        </div>

        {/* Upcoming releases */}
        <div className="card p-5">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold text-white">Next 30 days</h2>
            <Link href="/calendar" className="text-sm text-brand-400 hover:underline">
              Calendar
            </Link>
          </div>
          <div className="space-y-3">
            {upcomingReleases.length === 0 && (
              <p className="text-sm text-zinc-500">No releases scheduled.</p>
            )}
            {upcomingReleases.map((r) => (
              <div key={r.id} className="flex items-center gap-3">
                <div className="flex h-10 w-10 flex-col items-center justify-center rounded-lg bg-ink-800 text-center">
                  <span className="text-[10px] uppercase text-zinc-500">
                    {r.releaseDate.toLocaleString("en-US", { month: "short" })}
                  </span>
                  <span className="text-sm font-semibold text-white">
                    {r.releaseDate.getDate()}
                  </span>
                </div>
                <div className="min-w-0 flex-1">
                  <div className="truncate text-sm text-zinc-200">{r.title}</div>
                  <div className="text-xs text-zinc-500">
                    {r.client.name} · {r.kind}
                  </div>
                </div>
                {r.isPrimary && <Badge tone="brand">yours</Badge>}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Trending */}
      <div className="mt-6 card p-5">
        <h2 className="mb-4 font-semibold text-white">Trending &amp; news</h2>
        <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-3">
          {trends.length === 0 && (
            <p className="text-sm text-zinc-500">No trend data ingested yet.</p>
          )}
          {trends.map((t) => (
            <a
              key={t.id}
              href={t.url ?? "#"}
              target="_blank"
              rel="noreferrer"
              className="rounded-lg border border-white/5 bg-ink-800/50 p-3 hover:border-white/10"
            >
              <div className="text-xs text-zinc-500">{t.source}</div>
              <div className="mt-1 line-clamp-2 text-sm text-zinc-200">{t.title}</div>
            </a>
          ))}
        </div>
      </div>
    </div>
  );
}
