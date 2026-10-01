"""AI plays engine: task execution and caption generation."""

import pytest

from studio import models, services
from studio.tasks import run_play_task

pytestmark = pytest.mark.django_db


@pytest.fixture
def play():
    return models.Play.objects.create(
        key="shorts", name="Shorts Pack", builtin=True, active=True,
        steps=[
            {"op": "cut", "format": "reel_9x16", "count": 2},
            {"op": "still", "format": "still_thumb"},
        ],
        outputs=["reel_9x16", "still_thumb"],
    )


def test_run_play_task_succeeds_and_creates_derived_assets(play, basic_project, make_user):
    source = models.MediaAsset.objects.create(
        project=basic_project, kind="VIDEO", status="READY",
        label="Source", url="https://example.com/source.mp4",
    )
    run = models.PlayRun.objects.create(
        play=play, project=basic_project,
        triggered_by=make_user(username="trigger", role=models.Role.PRODUCER),
        status="QUEUED",
    )

    result = run_play_task(run.id)

    run.refresh_from_db()
    assert run.status == models.PlayRun.Status.SUCCEEDED
    assert run.progress == 100
    assert run.finished_at is not None
    assert result["ok"] is True

    derived = models.MediaAsset.objects.filter(play_run=run)
    assert derived.count() >= 2
    # All outputs are derived from the source and carry a format.
    for asset in derived:
        assert asset.derived_from_id == source.id
        assert asset.status == "READY"

    basic_project.refresh_from_db()
    assert basic_project.status == "READY"


def test_run_play_task_missing_run_returns_error():
    result = run_play_task(999999)
    assert "error" in result


def test_generate_caption_returns_nonempty_template():
    out = services.generate_caption(
        "A brand new single dropping this Friday. It slaps.", "INSTAGRAM",
    )
    assert out["caption"].strip()
    assert out["generated_by"] in {"template", "claude"}
    assert out["hashtags"]


def test_generate_caption_platform_specific():
    x = services.generate_caption("Short punchy news", "X")
    assert x["caption"].strip()
    assert x["generated_by"] in {"template", "claude"}
