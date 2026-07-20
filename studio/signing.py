"""Signed / expiring playback URLs for the paid video platform.

Members-only HLS content must not be hotlinkable. Two backends:

* **S3 / R2** (``AWS_STORAGE_BUCKET_NAME`` set): the storage backend already
  hands out short-lived signed URLs (``AWS_QUERYSTRING_AUTH``), so we just ask
  ``default_storage.url()`` for the object key.
* **Local FileSystemStorage** (dev / single-box): there is no per-object signing,
  so we mint a ``TimestampSigner`` token bound to the video id and route playback
  through the ``studio:hls_stream`` gate, which verifies + expires the token.
"""

from __future__ import annotations

from django.conf import settings
from django.core.files.storage import default_storage
from django.core.signing import BadSignature, SignatureExpired, TimestampSigner
from django.urls import reverse


def _signer() -> TimestampSigner:
    return TimestampSigner(salt=getattr(settings, "HLS_URL_SIGNING_SALT", "bcp-hls-signing"))


def signed_hls_url(video, request=None) -> str:
    """Return a signed, expiring playback URL for ``video``.

    On S3/R2, ``default_storage.url()`` is already a signed, expiring URL, so we
    return that directly for the stored HLS key. On local storage we sign the
    video id and point at the ``hls_stream`` gate.
    """
    hls_path = getattr(video, "hls_path", "") or ""

    if getattr(settings, "AWS_STORAGE_BUCKET_NAME", "") and hls_path:
        # S3/R2 storage key -> already signed + expiring by the backend.
        try:
            return default_storage.url(hls_path)
        except Exception:
            pass

    token = _signer().sign(f"{video.id}")
    path = reverse("studio:hls_stream", args=[video.id])
    return f"{path}?t={token}"


def verify_hls_token(video_id, token, max_age=3600) -> bool:
    """True if ``token`` is a valid, unexpired signature for ``video_id``."""
    if not token:
        return False
    try:
        value = _signer().unsign(token, max_age=max_age)
    except (BadSignature, SignatureExpired):
        return False
    return str(value) == str(video_id)
