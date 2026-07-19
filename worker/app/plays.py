"""AI Plays engine.

A "play" is a declarative pipeline of steps. This engine interprets those steps
and produces output media variants. When ffmpeg is available and a real source
file is on disk, it renders actual files (vertical cuts, squares, stills). When
it isn't, it emits the planned output specs so the rest of the platform stays
fully functional in demo/dev.

This mirrors the CDE/MDE "decompose a stream into every format" idea: one source
in, every deliverable out. Only the decoder (here, ffmpeg) changes.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import uuid

from .config import config
from .schemas import OutputSpec, RunPlayRequest

# format -> (kind, ffmpeg scale/crop filter, width x height)
FORMAT_SPECS: dict[str, tuple[str, str, tuple[int, int]]] = {
    "reel_9x16": ("VIDEO", "scale=1080:-2,crop=1080:1920", (1080, 1920)),
    "story_9x16": ("VIDEO", "scale=1080:-2,crop=1080:1920", (1080, 1920)),
    "square_1x1": ("VIDEO", "scale=1080:-2,crop=1080:1080", (1080, 1080)),
    "audiogram_1x1": ("VIDEO", "scale=1080:1080", (1080, 1080)),
    "banner_16x9": ("IMAGE", "scale=1920:-2,crop=1920:1080", (1920, 1080)),
    "still_thumb": ("IMAGE", "scale=1280:-2", (1280, 720)),
    "quote_card": ("IMAGE", "scale=1080:1080", (1080, 1080)),
    "transcript": ("DOCUMENT", "", (0, 0)),
}

# Human labels per format for nicer UI.
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
    if config.ENABLE_FFMPEG == "off":
        return False
    return shutil.which("ffmpeg") is not None


def _plan_outputs(req: RunPlayRequest) -> list[OutputSpec]:
    """Expand the declarative steps into concrete output specs."""
    outputs: list[OutputSpec] = []
    for step in req.steps:
        op = step.get("op")
        fmt = step.get("format")
        count = int(step.get("count") or 1)
        if op in {"cut", "audiogram", "story", "banner", "still"} and fmt:
            kind = FORMAT_SPECS.get(fmt, ("VIDEO", "", (0, 0)))[0]
            base = FORMAT_LABELS.get(fmt, fmt)
            for i in range(count):
                label = base if count == 1 else f"{base} #{i + 1}"
                outputs.append(OutputSpec(format=fmt, kind=kind, label=label))
        elif op == "quote_card":
            outputs.append(OutputSpec(format="quote_card", kind="IMAGE", label="Quote Card"))
        elif op == "export_transcript":
            outputs.append(OutputSpec(format="transcript", kind="DOCUMENT", label="Transcript"))
        elif op == "cover_from_art":
            outputs.append(OutputSpec(format="square_1x1", kind="IMAGE", label="Cover Post"))
    if not outputs:
        outputs = [OutputSpec(format="reel_9x16", kind="VIDEO", label="Vertical cut")]
    return outputs


def _render(req: RunPlayRequest, out: OutputSpec, workdir: str) -> None:
    """Render a single output with ffmpeg. Best-effort; mutates out.path on success."""
    src = req.mediaPath
    if not src or not os.path.exists(src):
        return
    spec = FORMAT_SPECS.get(out.format)
    if not spec:
        return
    _, vfilter, _ = spec
    ext = "mp4" if out.kind in {"VIDEO", "AUDIO"} else "jpg"
    dest = os.path.join(workdir, f"{out.format}_{uuid.uuid4().hex[:8]}.{ext}")
    if out.kind == "IMAGE":
        cmd = ["ffmpeg", "-y", "-i", src, "-vframes", "1"]
        if vfilter:
            cmd += ["-vf", vfilter]
        cmd += [dest]
    else:
        # take the first 30s as a stand-in highlight; a real detector would pick timestamps
        cmd = ["ffmpeg", "-y", "-i", src, "-t", "30"]
        if vfilter:
            cmd += ["-vf", vfilter]
        cmd += ["-c:a", "aac", dest]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
        out.path = dest
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
        out.path = None


def run_play(req: RunPlayRequest) -> tuple[list[OutputSpec], bool]:
    """Execute a play. Returns (outputs, rendered_real_files)."""
    outputs = _plan_outputs(req)
    real = False
    if ffmpeg_available() and req.mediaPath and os.path.exists(req.mediaPath):
        workdir = os.path.join(config.MEDIA_ROOT, req.playRunId)
        os.makedirs(workdir, exist_ok=True)
        for out in outputs:
            _render(req, out, workdir)
        real = any(o.path for o in outputs)
    return outputs, real
