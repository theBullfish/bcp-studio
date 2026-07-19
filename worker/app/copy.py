"""Copy generation — auto-write post captions from a user's summary.

Uses the Claude API when ANTHROPIC_API_KEY is set (real generation, brand-aware).
Falls back to a deterministic template so the platform always works offline.
"""

from __future__ import annotations

from .config import config
from .schemas import CaptionRequest, CaptionResponse

PLATFORM_GUIDE = {
    "INSTAGRAM": "1-3 short lines, an emoji or two, punchy hook first.",
    "TIKTOK": "One snappy hook line, casual, playful.",
    "YOUTUBE": "A title-like first line, then a short description.",
    "X": "Under 240 chars, punchy, at most one emoji.",
    "FACEBOOK": "Conversational, 2-3 sentences.",
    "LINKEDIN": "Professional but human, a hook then a takeaway.",
    "THREADS": "Casual and conversational, short.",
}


def _template_caption(req: CaptionRequest) -> str:
    summary = " ".join(req.summary.split())
    hook = summary.split(".")[0][:90] if summary else "New drop incoming"
    if req.platform == "X":
        return f"{hook} 🎧"
    if req.platform == "LINKEDIN":
        return f"{hook}.\n\nHere's what went into it 👇"
    if req.platform == "YOUTUBE":
        return f"{hook}\n\n{summary[:200]}"
    return f"{hook} 🔥\n\n{summary[:180]}".strip()


def _claude_caption(req: CaptionRequest) -> str | None:
    try:
        import anthropic
    except ImportError:
        return None
    try:
        client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
        guide = PLATFORM_GUIDE.get(req.platform, "Short and punchy.")
        tone = req.tone or "energetic, authentic, music-industry"
        msg = client.messages.create(
            model=config.ANTHROPIC_MODEL,
            max_tokens=300,
            system=(
                "You write social media captions for a record label. "
                "Return ONLY the caption text, no preamble, no quotes."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Write a {req.platform} caption.\n"
                        f"Brand tone of voice: {tone}\n"
                        f"Platform style: {guide}\n"
                        f"What the post is about: {req.summary}\n"
                        f"Do not include hashtags in the caption body."
                    ),
                }
            ],
        )
        parts = [b.text for b in msg.content if getattr(b, "type", None) == "text"]
        text = "".join(parts).strip()
        return text or None
    except Exception:
        return None


def generate_caption(req: CaptionRequest) -> CaptionResponse:
    hashtags = req.hashtags or "#ballsandchunk #newmusic"
    if config.has_anthropic:
        text = _claude_caption(req)
        if text:
            return CaptionResponse(caption=text, hashtags=hashtags, generatedBy="claude")
    return CaptionResponse(
        caption=_template_caption(req), hashtags=hashtags, generatedBy="template"
    )
