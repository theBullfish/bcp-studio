// Thin client for the Python worker (AI plays + copy generation).
// Everything degrades gracefully: if the worker is unreachable we return
// deterministic mock output so the product is always demoable.

const BASE = process.env.WORKER_URL ?? "http://localhost:8800";

async function call<T>(path: string, body: unknown, fallback: T): Promise<T> {
  try {
    const res = await fetch(`${BASE}${path}`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify(body),
      // worker jobs are quick to accept (they run async); short timeout is fine
      signal: AbortSignal.timeout(8000),
      cache: "no-store",
    });
    if (!res.ok) throw new Error(`worker ${res.status}`);
    return (await res.json()) as T;
  } catch {
    return fallback;
  }
}

export type PlayOutputSpec = { format: string; kind: string; label: string };

export const worker = {
  async runPlay(input: {
    playRunId: string;
    playKey: string;
    steps: unknown;
    mediaUrl?: string;
  }) {
    return call<{ accepted: boolean; outputs: PlayOutputSpec[] }>(
      "/plays/run",
      input,
      {
        accepted: true,
        outputs: mockOutputsFor(input.playKey),
      }
    );
  },

  async generateCaption(input: {
    summary: string;
    platform: string;
    tone?: string | null;
    hashtags?: string | null;
  }) {
    return call<{ caption: string; hashtags: string }>(
      "/copy/caption",
      input,
      {
        caption: mockCaption(input.summary, input.platform, input.tone),
        hashtags: input.hashtags ?? "#ballsandchunk #newmusic",
      }
    );
  },

  async health() {
    return call<{ ok: boolean }>("/health", {}, { ok: false });
  },
};

// ---- deterministic mocks (used when the worker is offline) ----

function mockOutputsFor(playKey: string): PlayOutputSpec[] {
  const packs: Record<string, PlayOutputSpec[]> = {
    shorts_pack: [
      { format: "reel_9x16", kind: "VIDEO", label: "Vertical Reel #1" },
      { format: "reel_9x16", kind: "VIDEO", label: "Vertical Reel #2" },
      { format: "reel_9x16", kind: "VIDEO", label: "Vertical Reel #3" },
      { format: "square_1x1", kind: "VIDEO", label: "Square teaser" },
      { format: "still_thumb", kind: "IMAGE", label: "Thumbnail still" },
    ],
    podcast_clips: [
      { format: "audiogram_1x1", kind: "VIDEO", label: "Audiogram clip #1" },
      { format: "audiogram_1x1", kind: "VIDEO", label: "Audiogram clip #2" },
      { format: "quote_card", kind: "IMAGE", label: "Quote card" },
      { format: "transcript", kind: "DOCUMENT", label: "Transcript" },
    ],
    release_kit: [
      { format: "reel_9x16", kind: "VIDEO", label: "Announcement reel" },
      { format: "square_1x1", kind: "IMAGE", label: "Cover post" },
      { format: "story_9x16", kind: "IMAGE", label: "Story sticker" },
      { format: "banner_16x9", kind: "IMAGE", label: "YouTube banner" },
    ],
  };
  return (
    packs[playKey] ?? [
      { format: "reel_9x16", kind: "VIDEO", label: "Vertical cut" },
      { format: "square_1x1", kind: "IMAGE", label: "Square post" },
    ]
  );
}

function mockCaption(summary: string, platform: string, tone?: string | null) {
  const s = summary.trim().replace(/\s+/g, " ");
  const hook = s.split(/[.!?]/)[0]?.slice(0, 80) || "New drop incoming";
  const flavor =
    platform === "X"
      ? `${hook} 🎧`
      : platform === "LINKEDIN"
        ? `${hook}.\n\nHere's what went into it 👇`
        : `${hook} 🔥\n\n${s.slice(0, 180)}`;
  return tone ? `${flavor}` : flavor;
}
