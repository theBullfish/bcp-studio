export function money(cents: number, currency = "USD"): string {
  return new Intl.NumberFormat("en-US", { style: "currency", currency }).format(
    cents / 100
  );
}

export function compactNumber(n: number): string {
  return new Intl.NumberFormat("en-US", { notation: "compact" }).format(n);
}

export function timeAgo(date: Date | string): string {
  const d = typeof date === "string" ? new Date(date) : date;
  const seconds = Math.floor((Date.now() - d.getTime()) / 1000);
  const table: [number, string][] = [
    [60, "s"],
    [3600, "m"],
    [86400, "h"],
    [604800, "d"],
    [2592000, "w"],
  ];
  if (seconds < 60) return "just now";
  for (let i = table.length - 1; i >= 0; i--) {
    const [limit, unit] = table[i];
    if (seconds >= limit) return `${Math.floor(seconds / limit)}${unit} ago`;
  }
  return "just now";
}

export const PLATFORM_META: Record<string, { label: string; color: string }> = {
  INSTAGRAM: { label: "Instagram", color: "#E1306C" },
  TIKTOK: { label: "TikTok", color: "#00f2ea" },
  YOUTUBE: { label: "YouTube", color: "#FF0000" },
  X: { label: "X", color: "#ffffff" },
  FACEBOOK: { label: "Facebook", color: "#1877F2" },
  LINKEDIN: { label: "LinkedIn", color: "#0A66C2" },
  THREADS: { label: "Threads", color: "#cccccc" },
};

export const STATUS_META: Record<string, { label: string; tone: string }> = {
  DRAFT: { label: "Draft", tone: "zinc" },
  IN_REVIEW: { label: "In review", tone: "amber" },
  APPROVED: { label: "Approved", tone: "emerald" },
  SCHEDULED: { label: "Scheduled", tone: "sky" },
  PUBLISHING: { label: "Publishing", tone: "violet" },
  PUBLISHED: { label: "Published", tone: "green" },
  FAILED: { label: "Failed", tone: "red" },
  REJECTED: { label: "Rejected", tone: "red" },
};
