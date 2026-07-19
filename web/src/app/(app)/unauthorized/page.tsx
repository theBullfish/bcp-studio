import Link from "next/link";

export default function Unauthorized() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center gap-3 text-center">
      <div className="text-4xl">🔒</div>
      <h1 className="text-xl font-semibold text-white">Not your pay grade</h1>
      <p className="max-w-sm text-sm text-zinc-400">
        Your role doesn&apos;t have access to this area. Ask an admin if you think
        that&apos;s wrong.
      </p>
      <Link href="/" className="btn-primary mt-2">
        Back to Control Room
      </Link>
    </div>
  );
}
