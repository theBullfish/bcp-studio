"""Balls & Chunk Studio worker.

Two jobs:
  - /plays/run   run an AI play: decompose one source into every deliverable format
  - /copy/caption generate a post caption from a summary (Claude-powered when configured)
"""

from __future__ import annotations

from fastapi import FastAPI

from .config import config
from .copy import generate_caption
from .plays import ffmpeg_available, run_play
from .schemas import (
    CaptionRequest,
    CaptionResponse,
    RunPlayRequest,
    RunPlayResponse,
)

app = FastAPI(title="BCP Studio Worker", version="0.1.0")


@app.get("/health")
@app.post("/health")
def health() -> dict:
    return {
        "ok": True,
        "ffmpeg": ffmpeg_available(),
        "anthropic": config.has_anthropic,
        "model": config.ANTHROPIC_MODEL if config.has_anthropic else None,
    }


@app.post("/plays/run", response_model=RunPlayResponse)
def plays_run(req: RunPlayRequest) -> RunPlayResponse:
    outputs, real = run_play(req)
    return RunPlayResponse(
        accepted=True, playRunId=req.playRunId, outputs=outputs, real=real
    )


@app.post("/copy/caption", response_model=CaptionResponse)
def copy_caption(req: CaptionRequest) -> CaptionResponse:
    return generate_caption(req)
