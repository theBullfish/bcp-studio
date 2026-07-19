import { getServerSession } from "next-auth";
import { redirect } from "next/navigation";
import type { Role } from "@prisma/client";
import { authOptions } from "./auth";

export type SessionUser = {
  id: string;
  email: string;
  name?: string | null;
  image?: string | null;
  role: Role;
};

// Ordered from most to least privileged. Index = rank.
const ROLE_RANK: Role[] = [
  "OWNER",
  "ADMIN",
  "PRODUCER",
  "EDITOR",
  "APPROVER",
  "CONTRIBUTOR",
  "VIEWER",
];

export function roleAtLeast(role: Role, minimum: Role): boolean {
  return ROLE_RANK.indexOf(role) <= ROLE_RANK.indexOf(minimum);
}

// Capability matrix — the single source of truth for "who can do what".
export const CAN = {
  manageUsers: (r: Role) => roleAtLeast(r, "ADMIN"),
  manageClients: (r: Role) => roleAtLeast(r, "ADMIN"),
  manageBilling: (r: Role) => r === "OWNER",
  createProject: (r: Role) => roleAtLeast(r, "PRODUCER"),
  runPlays: (r: Role) => roleAtLeast(r, "PRODUCER"),
  editMedia: (r: Role) => roleAtLeast(r, "EDITOR"),
  draftPost: (r: Role) => roleAtLeast(r, "CONTRIBUTOR"),
  schedulePost: (r: Role) => roleAtLeast(r, "PRODUCER"),
  approvePost: (r: Role) => roleAtLeast(r, "APPROVER"),
  viewAnalytics: (r: Role) => roleAtLeast(r, "VIEWER"),
  viewPay: (r: Role) => roleAtLeast(r, "ADMIN"),
} as const;

export async function getSessionUser(): Promise<SessionUser | null> {
  const session = await getServerSession(authOptions);
  if (!session?.user) return null;
  return session.user as unknown as SessionUser;
}

export async function requireUser(): Promise<SessionUser> {
  const user = await getSessionUser();
  if (!user) redirect("/login");
  return user;
}

export async function requireCapability(
  check: (r: Role) => boolean
): Promise<SessionUser> {
  const user = await requireUser();
  if (!check(user.role)) redirect("/unauthorized");
  return user;
}
