"""Key-authenticated ingest upload endpoint."""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from studio import models
from studio.ingest_models import Device, IngestedFile

pytestmark = pytest.mark.django_db


@pytest.fixture
def device(basic_client, basic_project):
    return Device.objects.create(
        name="Field Cam", client=basic_client, target_project=basic_project,
    )


def test_ingest_valid_key_creates_file_and_asset(client, device, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    url = reverse("studio:ingest_receive")
    upload = SimpleUploadedFile("clip.mp4", b"\x00\x01\x02fakevideo", content_type="video/mp4")

    resp = client.post(
        url, {"file": upload}, HTTP_X_DEVICE_KEY=device.api_key,
    )

    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert "media_id" in body

    ingested = IngestedFile.objects.get(id__gte=1)
    assert ingested.device_id == device.id
    assert ingested.status == IngestedFile.Status.PROCESSED

    media = models.MediaAsset.objects.get(id=body["media_id"])
    assert media.label == "clip.mp4"
    assert media.kind == models.MediaAsset.Kind.VIDEO
    assert media.project_id == device.target_project_id


def test_ingest_wrong_key_returns_401(client, device, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    url = reverse("studio:ingest_receive")
    upload = SimpleUploadedFile("clip.mp4", b"data", content_type="video/mp4")

    resp = client.post(url, {"file": upload}, HTTP_X_DEVICE_KEY="bcpk_wrongkey")

    assert resp.status_code == 401
    assert IngestedFile.objects.count() == 0
    assert models.MediaAsset.objects.count() == 0


def test_ingest_missing_key_returns_401(client, device, settings, tmp_path):
    settings.MEDIA_ROOT = str(tmp_path)
    url = reverse("studio:ingest_receive")
    upload = SimpleUploadedFile("clip.mp4", b"data", content_type="video/mp4")

    resp = client.post(url, {"file": upload})

    assert resp.status_code == 401


def test_ingest_get_not_allowed(client):
    resp = client.get(reverse("studio:ingest_receive"))
    assert resp.status_code == 405
