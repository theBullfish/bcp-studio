import clsx from "clsx";
import Link from "next/link";

export function PageHeader({
  title,
  subtitle,
  action,
}: {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}) {
  return (
    <div className="mb-6 flex items-end justify-between gap-4">
      <div>
        <h1 className="text-2xl font-semibold text-white">{title}</h1>
        {subtitle && <p className="mt-1 text-sm text-zinc-400">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

export function StatCard({
  label,
  value,
  hint,
  tone = "brand",
}: {
  label: string;
  value: string | number;
  hint?: string;
  tone?: "brand" | "emerald" | "amber" | "sky" | "red";
}) {
  const toneMap: Record<string, string> = {
    brand: "text-brand-400",
    emerald: "text-emerald-400",
    amber: "text-amber-400",
    sky: "text-sky-400",
    red: "text-red-400",
  };
  return (
    <div className="card p-4">
      <div className="text-xs uppercase tracking-wide text-zinc-500">{label}</div>
      <div className={clsx("mt-1 text-2xl font-semibold", toneMap[tone])}>
        {value}
      </div>
      {hint && <div className="mt-1 text-xs text-zinc-500">{hint}</div>}
    </div>
  );
}

const TONE_CLASS: Record<string, string> = {
  zinc: "bg-zinc-500/15 text-zinc-300",
  amber: "bg-amber-500/15 text-amber-300",
  emerald: "bg-emerald-500/15 text-emerald-300",
  green: "bg-green-500/15 text-green-300",
  sky: "bg-sky-500/15 text-sky-300",
  violet: "bg-violet-500/15 text-violet-300",
  red: "bg-red-500/15 text-red-300",
  brand: "bg-brand-600/20 text-brand-400",
};

export function Badge({
  children,
  tone = "zinc",
}: {
  children: React.ReactNode;
  tone?: string;
}) {
  return (
    <span className={clsx("pill", TONE_CLASS[tone] ?? TONE_CLASS.zinc)}>
      {children}
    </span>
  );
}

export function EmptyState({
  title,
  hint,
  cta,
}: {
  title: string;
  hint?: string;
  cta?: { href: string; label: string };
}) {
  return (
    <div className="card flex flex-col items-center justify-center gap-3 p-12 text-center">
      <div className="text-lg font-medium text-zinc-300">{title}</div>
      {hint && <div className="max-w-md text-sm text-zinc-500">{hint}</div>}
      {cta && (
        <Link href={cta.href} className="btn-primary mt-2">
          {cta.label}
        </Link>
      )}
    </div>
  );
}
