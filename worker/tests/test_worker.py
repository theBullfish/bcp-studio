from app.copy import generate_caption
from app.plays import run_play
from app.schemas import CaptionRequest, RunPlayRequest


def test_shorts_pack_plans_outputs():
    req = RunPlayRequest(
        playRunId="run1",
        playKey="shorts_pack",
        steps=[
            {"op": "cut", "format": "reel_9x16", "count": 3},
            {"op": "cut", "format": "square_1x1", "count": 1},
            {"op": "still", "format": "still_thumb"},
        ],
    )
    outputs, real = run_play(req)
    formats = [o.format for o in outputs]
    assert formats.count("reel_9x16") == 3
    assert "square_1x1" in formats
    assert "still_thumb" in formats
    assert real is False  # no source file on disk


def test_caption_template_fallback():
    req = CaptionRequest(summary="New single drops Friday.", platform="X")
    res = generate_caption(req)
    assert res.caption
    assert res.generatedBy in {"claude", "template"}
    # X captions stay short
    assert len(res.caption) < 280
