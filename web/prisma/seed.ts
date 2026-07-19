import { PrismaClient, Platform } from "@prisma/client";
import bcrypt from "bcryptjs";

const prisma = new PrismaClient();

// Deterministic pseudo-random so re-seeding gives stable-ish numbers.
let s = 42;
const rand = () => ((s = (s * 1103515245 + 12345) & 0x7fffffff) / 0x7fffffff);
const pick = <T>(a: T[]) => a[Math.floor(rand() * a.length)];
const int = (min: number, max: number) => Math.floor(min + rand() * (max - min));
const daysFromNow = (d: number) => new Date(Date.now() + d * 864e5);

async function main() {
  console.log("Seeding BCP Studio…");

  // ---- Users --------------------------------------------------------------
  const pw = await bcrypt.hash("chunk1234", 10);
  const users = await Promise.all(
    [
      { email: "owner@ballsandchunk.com", name: "Brad Svenson", role: "OWNER" as const, payRateCents: 0 },
      { email: "admin@ballsandchunk.com", name: "Dana Ruiz", role: "ADMIN" as const, payRateCents: 6500 },
      { email: "producer@ballsandchunk.com", name: "Marcus Lee", role: "PRODUCER" as const, payRateCents: 5500 },
      { email: "editor@ballsandchunk.com", name: "Priya Shah", role: "EDITOR" as const, payRateCents: 4500 },
      { email: "approver@ballsandchunk.com", name: "Toni Blake", role: "APPROVER" as const, payRateCents: 5000 },
      { email: "contributor@ballsandchunk.com", name: "Sam Ortiz", role: "CONTRIBUTOR" as const, payRateCents: 3500 },
    ].map((u) =>
      prisma.user.upsert({
        where: { email: u.email },
        update: {},
        create: { ...u, passwordHash: pw },
      })
    )
  );
  const owner = users[0];
  const producer = users[2];
  const approver = users[4];

  // ---- Clients + brand kits ----------------------------------------------
  const clientDefs = [
    { name: "Balls & Chunk Productions", slug: "balls-and-chunk", primary: "#6d28d9", accent: "#f59e0b", tone: "Raw, funny, hip-hop energy. Punchy. Never corporate." },
    { name: "Neon Alley Records", slug: "neon-alley", primary: "#0ea5e9", accent: "#ec4899", tone: "Slick, nightlife, synthwave. Confident and cool." },
    { name: "Deep Cut Podcast Network", slug: "deep-cut", primary: "#10b981", accent: "#f43f5e", tone: "Thoughtful, curious, conversational. Smart but warm." },
  ];
  const clients = [];
  for (const c of clientDefs) {
    const client = await prisma.client.upsert({
      where: { slug: c.slug },
      update: {},
      create: {
        name: c.name,
        slug: c.slug,
        brandKit: {
          create: {
            primaryColor: c.primary,
            secondaryColor: "#0a0a0f",
            accentColor: c.accent,
            fontHeading: "Inter",
            fontBody: "Inter",
            toneOfVoice: c.tone,
            hashtagsCsv: "#newmusic,#indie,#nowplaying",
            logoMarkUrl: null,
          },
        },
        socialAccounts: {
          create: [
            { platform: "INSTAGRAM", handle: `@${c.slug}`, connected: true },
            { platform: "TIKTOK", handle: `@${c.slug}`, connected: true },
            { platform: "YOUTUBE", handle: c.name, connected: true },
            { platform: "X", handle: `@${c.slug}`, connected: false },
          ],
        },
      },
      include: { socialAccounts: true },
    });
    clients.push(client);
    // memberships
    for (const u of users) {
      await prisma.clientMembership.upsert({
        where: { userId_clientId: { userId: u.id, clientId: client.id } },
        update: {},
        create: { userId: u.id, clientId: client.id },
      });
    }
  }

  // ---- Builtin plays ------------------------------------------------------
  const plays = [
    {
      key: "shorts_pack",
      name: "Shorts Pack",
      description: "Turn one long video into 3 vertical reels, a square teaser, and a thumbnail.",
      steps: [
        { op: "transcribe" },
        { op: "detect_highlights", count: 3 },
        { op: "cut", format: "reel_9x16", count: 3, captions: true },
        { op: "cut", format: "square_1x1", count: 1 },
        { op: "still", format: "still_thumb" },
        { op: "brand_overlay" },
      ],
      outputs: ["reel_9x16", "square_1x1", "still_thumb"],
    },
    {
      key: "podcast_clips",
      name: "Podcast Clips",
      description: "Audiograms, quote cards, and a transcript from an episode.",
      steps: [
        { op: "transcribe" },
        { op: "detect_quotes", count: 2 },
        { op: "audiogram", format: "audiogram_1x1", count: 2 },
        { op: "quote_card" },
        { op: "export_transcript" },
      ],
      outputs: ["audiogram_1x1", "quote_card", "transcript"],
    },
    {
      key: "release_kit",
      name: "Release Kit",
      description: "Full announcement kit for a new single or album drop.",
      steps: [
        { op: "cover_from_art" },
        { op: "cut", format: "reel_9x16", count: 1 },
        { op: "story", format: "story_9x16" },
        { op: "banner", format: "banner_16x9" },
        { op: "brand_overlay" },
      ],
      outputs: ["reel_9x16", "square_1x1", "story_9x16", "banner_16x9"],
    },
  ];
  for (const p of plays) {
    await prisma.play.upsert({
      where: { key: p.key },
      update: {},
      create: { ...p, builtin: true },
    });
  }

  // ---- Projects, media, posts, metrics -----------------------------------
  const projectTitles = [
    "Midnight Freestyle Session",
    "Studio Vlog — Ep. 12",
    "New Single: 'Gravel'",
    "Deep Cut #48: The Sample Debate",
    "Rooftop Live Set",
  ];
  const platforms: Platform[] = ["INSTAGRAM", "TIKTOK", "YOUTUBE", "X"];
  const captions = [
    "Behind the boards on the new one. This beat almost didn't make it 😅",
    "3AM in the booth hits different. Full track drops Friday 🔥",
    "You asked, we delivered. 'Gravel' is out everywhere now.",
    "Hot take: the sample makes the song. Fight us in the comments.",
    "Rooftop set was unreal. Swipe for the full moment.",
  ];

  for (let i = 0; i < projectTitles.length; i++) {
    const client = clients[i % clients.length];
    const project = await prisma.project.create({
      data: {
        clientId: client.id,
        ownerId: pick([owner.id, producer.id]),
        title: projectTitles[i],
        summary: captions[i],
        status: pick(["READY", "SCHEDULED", "PROCESSING"] as const),
        media: {
          create: [
            {
              kind: "VIDEO",
              status: "READY",
              label: "Source recording",
              url: "https://example.com/source.mp4",
              durationMs: int(60000, 900000),
              uploaderId: producer.id,
            },
            {
              kind: "VIDEO",
              status: "READY",
              label: "Vertical Reel #1",
              url: "https://example.com/reel1.mp4",
              format: "reel_9x16",
              durationMs: int(15000, 45000),
            },
            {
              kind: "IMAGE",
              status: "READY",
              label: "Thumbnail still",
              url: "https://example.com/thumb.jpg",
              format: "still_thumb",
            },
          ],
        },
      },
    });

    // one or two posts per project
    for (let j = 0; j < int(1, 3); j++) {
      const platform = pick(platforms);
      const acct = await prisma.socialAccount.findFirst({
        where: { clientId: client.id, platform },
      });
      const status = pick(["PUBLISHED", "SCHEDULED", "IN_REVIEW", "DRAFT"] as const);
      const post = await prisma.post.create({
        data: {
          clientId: client.id,
          projectId: project.id,
          authorId: pick([producer.id, owner.id]),
          socialAccountId: acct?.id,
          platform,
          status,
          caption: captions[i],
          captionAi: captions[i],
          hashtags: "#ballsandchunk #newmusic #studio",
          scheduledAt: status === "SCHEDULED" ? daysFromNow(int(1, 21)) : null,
          publishedAt: status === "PUBLISHED" ? daysFromNow(-int(1, 30)) : null,
          externalUrl: status === "PUBLISHED" ? "https://instagram.com/p/demo" : null,
        },
      });

      if (status === "IN_REVIEW") {
        await prisma.approval.create({
          data: { postId: post.id, reviewerId: approver.id, decision: "PENDING" },
        });
      }
      if (status === "PUBLISHED") {
        await prisma.postMetric.create({
          data: {
            postId: post.id,
            impressions: int(2000, 90000),
            reach: int(1500, 70000),
            likes: int(100, 6000),
            comments: int(5, 400),
            shares: int(2, 800),
            saves: int(10, 1200),
            views: int(3000, 150000),
            clicks: int(20, 900),
            revenueCents: int(0, 40000),
          },
        });
      }
    }

    // a release for some projects
    if (i % 2 === 0) {
      await prisma.release.create({
        data: {
          clientId: client.id,
          projectId: project.id,
          title: projectTitles[i],
          kind: pick(["SINGLE", "VIDEO", "EPISODE", "ALBUM"] as const),
          releaseDate: daysFromNow(int(-10, 28)),
          isPrimary: client.slug === "balls-and-chunk",
        },
      });
    }
  }

  // ---- Revenue ------------------------------------------------------------
  for (const client of clients) {
    for (let m = 0; m < 6; m++) {
      await prisma.revenueEntry.create({
        data: {
          clientId: client.id,
          source: pick(["STREAMING", "MERCH", "SYNC", "AD_REVENUE", "SPONSORSHIP"] as const),
          amountCents: int(20000, 350000),
          occurredAt: daysFromNow(-m * 30 - int(0, 20)),
        },
      });
    }
  }

  // ---- Pay entries --------------------------------------------------------
  for (const u of users) {
    if (!u.payRateCents) continue;
    await prisma.payEntry.create({
      data: {
        userId: u.id,
        amountCents: u.payRateCents * int(20, 80),
        periodStart: daysFromNow(-14),
        periodEnd: new Date(),
        paid: false,
      },
    });
  }

  // ---- Trends -------------------------------------------------------------
  const trends = [
    { source: "google-trends", title: "Indie hip-hop streams up 24% this quarter", category: "industry" },
    { source: "rss:pitchfork", title: "The return of the physical single", category: "news" },
    { source: "tiktok-sounds", title: "Slowed + reverb trend resurging", category: "trend" },
    { source: "google-trends", title: "'Type beat' searches spike on weekends", category: "trend" },
    { source: "rss:billboard", title: "Short-form video now drives 60% of discovery", category: "news" },
  ];
  for (const t of trends) {
    await prisma.trendItem.create({ data: { ...t, score: rand(), url: "https://example.com" } });
  }

  // ---- A demo conversation -----------------------------------------------
  const convo = await prisma.conversation.create({
    data: {
      title: "Friday drop plan",
      participants: { create: [{ userId: owner.id }, { userId: producer.id }, { userId: approver.id }] },
    },
  });
  await prisma.message.createMany({
    data: [
      { conversationId: convo.id, senderId: producer.id, body: "Reels for 'Gravel' are cut and in review 🎬" },
      { conversationId: convo.id, senderId: approver.id, body: "Looking now — approving the first two." },
      { conversationId: convo.id, senderId: owner.id, body: "🔥 ship it Friday 9am like usual" },
    ],
  });

  console.log("Seed complete.");
  console.log("Login: owner@ballsandchunk.com / chunk1234");
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(() => prisma.$disconnect());
