"""Studio services — the AI 'plays' engine and caption generation.

Folded in from the standalone worker so the Django app runs it directly. In
production the heavy media rendering would move to a Celery task; the interface
here stays the same. Everything degrades gracefully so the platform always works.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import uuid

from django.conf import settings

# format -> (media kind, ffmpeg vf filter)
FORMAT_SPECS = {
    "reel_9x16": ("VIDEO", "scale=1080:-2,crop=1080:1920"),
    "story_9x16": ("VIDEO", "scale=1080:-2,crop=1080:1920"),
    "square_1x1": ("VIDEO", "scale=1080:-2,crop=1080:1080"),
    "audiogram_1x1": ("VIDEO", "scale=1080:1080"),
    "banner_16x9": ("IMAGE", "scale=1920:-2,crop=1920:1080"),
    "still_thumb": ("IMAGE", "scale=1280:-2"),
    "quote_card": ("IMAGE", "scale=1080:1080"),
    "transcript": ("DOCUMENT", ""),
}

FORMAT_LABELS = {
    "reel_9x16": "Vertical Reel",
    "story_9x16": "Story",
    "square_1x1": "Square Post",
    "audiogram_1x1": "Audiogram",
    "banner_16x9": "Banner",
    "still_thumb": "Thumbnail",
    "quote_card": "Quote Card",
    "transcript": "Transcript",
}


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def plan_play_outputs(steps: list[dict]) -> list[dict]:
    """Expand a play's declarative steps into concrete output specs."""
    outputs: list[dict] = []
    for step in steps or []:
        op = step.get("op")
        fmt = step.get("format")
        count = int(step.get("count") or 1)
        if op in {"cut", "audiogram", "story", "banner", "still"} and fmt:
            kind = FORMAT_SPECS.get(fmt, ("VIDEO", ""))[0]
            base = FORMAT_LABELS.get(fmt, fmt)
            for i in range(count):
                label = base if count == 1 else f"{base} #{i + 1}"
                outputs.append({"format": fmt, "kind": kind, "label": label})
        elif op == "quote_card":
            outputs.append({"format": "quote_card", "kind": "IMAGE", "label": "Quote Card"})
        elif op == "export_transcript":
            outputs.append({"format": "transcript", "kind": "DOCUMENT", "label": "Transcript"})
        elif op == "cover_from_art":
            outputs.append({"format": "square_1x1", "kind": "IMAGE", "label": "Cover Post"})
    if not outputs:
        outputs = [{"format": "reel_9x16", "kind": "VIDEO", "label": "Vertical cut"}]
    return outputs


def render_output(source_path: str, fmt: str, workdir: str) -> str | None:
    """Best-effort ffmpeg render of a single output. Returns a path or None."""
    spec = FORMAT_SPECS.get(fmt)
    if not spec or not source_path or not os.path.exists(source_path):
        return None
    kind, vfilter = spec
    ext = "jpg" if kind == "IMAGE" else "mp4"
    dest = os.path.join(workdir, f"{fmt}_{uuid.uuid4().hex[:8]}.{ext}")
    if kind == "IMAGE":
        cmd = ["ffmpeg", "-y", "-i", source_path, "-vframes", "1"]
    else:
        cmd = ["ffmpeg", "-y", "-i", source_path, "-t", "30"]
    if vfilter:
        cmd += ["-vf", vfilter]
    cmd += [dest]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        return dest
    except Exception:
        return None


def run_play(steps: list[dict], source_path: str | None = None, run_id: str = "run") -> tuple[list[dict], bool]:
    """Execute a play. Returns (outputs, rendered_real_files)."""
    outputs = plan_play_outputs(steps)
    real = False
    if ffmpeg_available() and source_path and os.path.exists(source_path):
        workdir = os.path.join(getattr(settings, "MEDIA_ROOT", "/tmp/bcp-media"), run_id)
        os.makedirs(workdir, exist_ok=True)
        for out in outputs:
            path = render_output(source_path, out["format"], workdir)
            if path:
                out["path"] = path
                real = True
    return outputs, real


# ---------------------------------------------------------------------------
# Caption generation
# ---------------------------------------------------------------------------

PLATFORM_GUIDE = {
    "INSTAGRAM": "1-3 short lines, an emoji or two, punchy hook first.",
    "TIKTOK": "One snappy hook line, casual, playful.",
    "YOUTUBE": "A title-like first line, then a short description.",
    "X": "Under 240 chars, punchy, at most one emoji.",
    "FACEBOOK": "Conversational, 2-3 sentences.",
    "LINKEDIN": "Professional but human, a hook then a takeaway.",
    "THREADS": "Casual and conversational, short.",
}


def _template_caption(summary: str, platform: str) -> str:
    s = " ".join((summary or "").split())
    hook = s.split(".")[0][:90] if s else "New drop incoming"
    if platform == "X":
        return f"{hook} 🎧"
    if platform == "LINKEDIN":
        return f"{hook}.\n\nHere's what went into it 👇"
    if platform == "YOUTUBE":
        return f"{hook}\n\n{s[:200]}"
    return f"{hook} 🔥\n\n{s[:180]}".strip()


def generate_caption(summary: str, platform: str, tone: str = "", hashtags: str = "") -> dict:
    """Claude-powered when ANTHROPIC_API_KEY is set; template fallback otherwise."""
    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    tags = hashtags or "#ballsandchunk #newmusic"
    if api_key:
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=api_key)
            guide = PLATFORM_GUIDE.get(platform, "Short and punchy.")
            msg = client.messages.create(
                model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5"),
                max_tokens=300,
                system=(
                    "You write social media captions for a record label. "
                    "Return ONLY the caption text, no preamble, no quotes."
                ),
                messages=[
                    {
                        "role": "user",
                        "content": (
                            f"Write a {platform} caption.\n"
                            f"Brand tone of voice: {tone or 'energetic, authentic, music-industry'}\n"
                            f"Platform style: {guide}\n"
                            f"What the post is about: {summary}\n"
                            f"Do not include hashtags in the caption body."
                        ),
                    }
                ],
            )
            text = "".join(b.text for b in msg.content if getattr(b, "type", None) == "text").strip()
            if text:
                return {"caption": text, "hashtags": tags, "generated_by": "claude"}
        except Exception:
            pass
    return {"caption": _template_caption(summary, platform), "hashtags": tags, "generated_by": "template"}
