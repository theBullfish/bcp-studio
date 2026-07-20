"""In-browser quick-finish editor backend — trim + burn-in caption.

A lightweight companion to services.py's play engine: given a source video and
an in/out point (seconds) plus an optional caption, ffmpeg trims the clip and
burns a simple drawtext caption over it. The result is saved as a NEW derived
MediaAsset so the original is never touched.

Everything degrades gracefully: with no ffmpeg (or a missing/remote source) the
task still creates the derived MediaAsset row (pointing at the original source),
so the finish → approve → post flow keeps working in dev.
"""

from __future__ import annotations

import os
import subprocess
import uuid

from celery import shared_task
from django.conf import settings

from .services import ffmpeg_available


def _escape_drawtext(text: str) -> str:
    """Escape a caption string for ffmpeg's drawtext filter."""
    # Order matters: backslashes first, then the characters drawtext treats
    # specially inside the single-quoted text= value.
    out = text.replace("\\", "\\\\")
    out = out.replace(":", r"\:")
    out = out.replace("'", r"\'")
    out = out.replace("%", r"\%")
    out = out.replace("\n", " ")
    return out


def trim_and_caption(
    src_path: str,
    out_dir: str,
    start_sec: float,
    end_sec: float,
    caption_text: str = "",
) -> str | None:
    """Trim ``src_path`` from start→end and optionally burn a caption.

    Returns the output mp4 path, or None if ffmpeg is unavailable or the source
    file is missing/unreadable. Guarded exactly like services.transcode_to_hls.
    """
    if not (ffmpeg_available() and src_path and os.path.exists(src_path)):
        return None

    try:
        start = max(0.0, float(start_sec))
        end = float(end_sec)
    except (TypeError, ValueError):
        return None
    duration = end - start
    if duration <= 0:
        return None

    os.makedirs(out_dir, exist_ok=True)
    dest = os.path.join(out_dir, f"edit_{uuid.uuid4().hex[:8]}.mp4")

    cmd = [
        "ffmpeg", "-y",
        "-ss", f"{start:.3f}",
        "-i", src_path,
        "-t", f"{duration:.3f}",
    ]
    if caption_text:
        caption = _escape_drawtext(caption_text)
        drawtext = (
            "drawtext=text='%s':fontcolor=white:fontsize=42:box=1:boxcolor=black@0.5:"
            "boxborderw=12:x=(w-text_w)/2:y=h-(text_h*2)" % caption
        )
        cmd += ["-vf", drawtext]
    cmd += ["-c:a", "aac", dest]

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=600)
        return dest
    except Exception:
        return None


@shared_task
def trim_media_task(media_id, start_sec, end_sec, caption_text=""):
    """Render a trimmed/captioned edit of a MediaAsset into a new derived asset.

    The original asset is left untouched. On success (or graceful ffmpeg-less
    fallback) a new MediaAsset(derived_from=original, status=READY) is created.
    Returns ``{"ok": True, "media_id": <new id>}``.
    """
    from . import models

    original = models.MediaAsset.objects.filter(id=media_id).first()
    if not original:
        return {"error": "media not found"}

    out_dir = os.path.join(settings.MEDIA_ROOT, "edits", str(original.id))
    src_path = original.url or ""

    output_path = trim_and_caption(src_path, out_dir, start_sec, end_sec, caption_text)

    # Graceful fallback: with no ffmpeg (or a remote/missing source) we still
    # create the derived row so the flow works — it just points at the source.
    url = output_path or src_path

    new = models.MediaAsset.objects.create(
        project=original.project,
        uploader=original.uploader,
        kind=models.MediaAsset.Kind.VIDEO,
        status=models.MediaAsset.Status.READY,
        label=f"{original.label} (edited)",
        url=url,
        format=original.format,
        derived_from=original,
    )
    return {"ok": True, "media_id": new.id}
