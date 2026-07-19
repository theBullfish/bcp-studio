"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { signOut } from "next-auth/react";
import clsx from "clsx";

const NAV: { href: string; label: string; icon: string }[] = [
  { href: "/", label: "Control Room", icon: "◎" },
  { href: "/projects", label: "Projects", icon: "▤" },
  { href: "/plays", label: "AI Plays", icon: "⚡" },
  { href: "/posts", label: "Posts & Schedule", icon: "✎" },
  { href: "/calendar", label: "Calendar", icon: "▦" },
  { href: "/approvals", label: "Approvals", icon: "✔" },
  { href: "/clients", label: "Clients", icon: "◆" },
  { href: "/analytics", label: "Analytics", icon: "▨" },
  { href: "/messages", label: "Messages", icon: "✉" },
  { href: "/team", label: "Team", icon: "☺" },
];

export function Sidebar({ role, name }: { role: string; name?: string | null }) {
  const pathname = usePathname();
  return (
    <aside className="flex w-60 shrink-0 flex-col border-r border-white/10 bg-ink-900/60 px-3 py-4">
      <div className="mb-6 flex items-center gap-2 px-2">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-xs font-black text-white">
          B&amp;C
        </div>
        <div className="leading-tight">
          <div className="text-sm font-semibold text-white">Studio</div>
          <div className="text-[10px] uppercase tracking-wide text-zinc-500">
            Balls &amp; Chunk
          </div>
        </div>
      </div>

      <nav className="flex-1 space-y-1">
        {NAV.map((item) => {
          const active =
            item.href === "/"
              ? pathname === "/"
              : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={clsx(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm transition",
                active
                  ? "bg-brand-600/20 text-white"
                  : "text-zinc-400 hover:bg-white/5 hover:text-zinc-200"
              )}
            >
              <span className="w-4 text-center text-zinc-500">{item.icon}</span>
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="mt-4 border-t border-white/10 pt-3">
        <div className="px-3 pb-2">
          <div className="truncate text-sm text-zinc-200">{name ?? "User"}</div>
          <div className="text-[10px] uppercase tracking-wide text-brand-400">
            {role}
          </div>
        </div>
        <button
          onClick={() => signOut({ callbackUrl: "/login" })}
          className="w-full rounded-lg px-3 py-2 text-left text-sm text-zinc-400 hover:bg-white/5 hover:text-zinc-200"
        >
          Sign out
        </button>
      </div>
    </aside>
  );
}
