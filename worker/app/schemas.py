from __future__ import annotations

from pydantic import BaseModel, Field


class PlayStep(BaseModel):
    op: str
    format: str | None = None
    count: int | None = None
    captions: bool | None = None


class RunPlayRequest(BaseModel):
    playRunId: str
    playKey: str
    steps: list[dict] = Field(default_factory=list)
    mediaUrl: str | None = None
    mediaPath: str | None = None  # local path if the source is already on disk


class OutputSpec(BaseModel):
    format: str
    kind: str  # VIDEO | AUDIO | IMAGE | DOCUMENT
    label: str
    path: str | None = None  # populated when real files are produced


class RunPlayResponse(BaseModel):
    accepted: bool
    playRunId: str
    outputs: list[OutputSpec]
    real: bool = False  # True when ffmpeg actually rendered files


class CaptionRequest(BaseModel):
    summary: str
    platform: str
    tone: str | None = None
    hashtags: str | None = None


class CaptionResponse(BaseModel):
    caption: str
    hashtags: str
    generatedBy: str  # "claude" | "template"
