#!/usr/bin/env python3
"""BCP Studio sync agent — Tailscale record → sync.

Runs on a capture machine (e.g. a recording laptop) on your Tailscale tailnet.
Watches a folder, waits for each file to finish writing (stable size between
polls), then uploads it to the media server's ingest endpoint over the tailnet.

State is persisted to ~/.bcp_sync_state.json so already-uploaded files are never
re-sent and uploads resume across restarts. Network errors retry with exponential
backoff. The loop keeps running so it rides through flaky wifi.

Dependencies: Python 3.8+ stdlib + `requests` (pip install requests).

Usage:
    python agent.py --server http://100.101.102.103:8000 \
                    --key bcpk_XXXXXXXX --watch ~/Recordings
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

try:
    import requests  # pip install requests
except ImportError:  # pragma: no cover
    sys.stderr.write("This agent needs `requests`. Install it with: pip install requests\n")
    sys.exit(1)


STATE_PATH = Path.home() / ".bcp_sync_state.json"
BACKOFF_SCHEDULE = [2, 4, 8, 16]  # seconds; last value repeats


def log(msg: str) -> None:
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


# ---------------------------------------------------------------------------
# State — records which files we've already uploaded, keyed path+mtime+size.
# ---------------------------------------------------------------------------


def load_state() -> dict:
    if STATE_PATH.exists():
        try:
            with STATE_PATH.open("r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict) and "uploaded" in data:
                return data
        except (json.JSONDecodeError, OSError) as exc:
            log(f"warning: could not read state file ({exc}); starting fresh")
    return {"uploaded": {}}


def save_state(state: dict) -> None:
    tmp = STATE_PATH.with_suffix(".tmp")
    try:
        with tmp.open("w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2)
        tmp.replace(STATE_PATH)
    except OSError as exc:
        log(f"warning: could not write state file ({exc})")


def file_signature(path: Path) -> str:
    st = path.stat()
    return f"{path.resolve()}|{int(st.st_mtime)}|{st.st_size}"


# ---------------------------------------------------------------------------
# Upload with exponential backoff retry.
# ---------------------------------------------------------------------------


def upload_file(server: str, key: str, path: Path) -> bool:
    url = server.rstrip("/") + "/ingest/"
    headers = {"X-Device-Key": key}

    attempt = 0
    while True:
        try:
            with path.open("rb") as fh:
                resp = requests.post(
                    url,
                    headers=headers,
                    files={"file": (path.name, fh)},
                    timeout=300,
                )
            if resp.status_code == 200:
                try:
                    body = resp.json()
                except ValueError:
                    body = {}
                log(f"uploaded {path.name} -> media_id={body.get('media_id')} "
                    f"project_id={body.get('project_id')}")
                return True

            if resp.status_code == 401:
                log(f"ERROR: unauthorized (401) uploading {path.name} — check --key. Skipping.")
                return False

            # Other HTTP errors: server-side. Log and give up on this file for now;
            # it stays un-recorded so we retry it on the next poll.
            log(f"server returned {resp.status_code} for {path.name}: {resp.text[:200]}")
            return False

        except requests.RequestException as exc:
            wait = BACKOFF_SCHEDULE[min(attempt, len(BACKOFF_SCHEDULE) - 1)]
            log(f"network error uploading {path.name} ({exc}); retrying in {wait}s")
            time.sleep(wait)
            attempt += 1
            if attempt > 8:  # ~ a couple minutes of retries, then defer to next poll
                log(f"giving up on {path.name} for now; will retry on next poll")
                return False


# ---------------------------------------------------------------------------
# Watch loop.
# ---------------------------------------------------------------------------


def iter_files(watch_dir: Path):
    for root, _dirs, names in os.walk(watch_dir):
        for name in names:
            if name.startswith("."):
                continue  # skip dotfiles / in-progress temp files
            yield Path(root) / name


def run(server: str, key: str, watch: str, interval: float) -> None:
    watch_dir = Path(os.path.expanduser(watch)).resolve()
    if not watch_dir.is_dir():
        log(f"ERROR: watch folder does not exist: {watch_dir}")
        sys.exit(1)

    state = load_state()
    uploaded = state["uploaded"]
    # Tracks last-seen size per path so we only upload once a file stops growing.
    pending_sizes: dict[str, int] = {}

    log(f"watching {watch_dir}")
    log(f"server {server}  interval {interval}s")

    while True:
        try:
            for path in iter_files(watch_dir):
                try:
                    sig = file_signature(path)
                except OSError:
                    continue  # file vanished mid-scan

                if sig in uploaded:
                    continue

                key_path = str(path.resolve())
                size = path.stat().st_size
                last_size = pending_sizes.get(key_path)

                if last_size != size:
                    # Still being written (or first time we've seen it). Wait for
                    # the next poll to confirm the size is stable.
                    pending_sizes[key_path] = size
                    continue

                # Size stable across two polls => finished writing. Upload it.
                if upload_file(server, key, path):
                    uploaded[sig] = {"name": path.name, "at": time.time()}
                    save_state(state)
                    pending_sizes.pop(key_path, None)

        except Exception as exc:  # noqa: BLE001 — never let the loop die
            log(f"unexpected error in scan loop: {exc}")

        time.sleep(interval)


def main() -> None:
    parser = argparse.ArgumentParser(description="BCP Studio Tailscale sync agent")
    parser.add_argument("--server", required=True,
                        help="Media server base URL, e.g. http://100.101.102.103:8000")
    parser.add_argument("--key", required=True, help="Device API key (bcpk_...)")
    parser.add_argument("--watch", required=True, help="Folder to watch for new recordings")
    parser.add_argument("--interval", type=float, default=5.0,
                        help="Poll interval in seconds (default: 5)")
    args = parser.parse_args()

    try:
        run(args.server, args.key, args.watch, args.interval)
    except KeyboardInterrupt:
        log("stopped")


if __name__ == "__main__":
    main()
