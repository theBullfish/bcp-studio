"""URL patterns for storage-backed uploads, the quick-finish editor, and the
signed HLS playback gate.

Plain urlpatterns (no app_name) — included by the project root urls under the
same 'studio' namespace as the rest of the app, so {% url 'studio:media_upload' %}
etc. resolve.
"""

from django.urls import path

from . import views_media as v

urlpatterns = [
    # Uploads (GET form + POST multipart)
    path("projects/<int:project_id>/upload/", v.media_upload, name="media_upload"),
    # Quick-finish editor
    path("media/<int:media_id>/edit/", v.media_edit, name="media_edit"),
    path("media/<int:media_id>/apply/", v.media_apply, name="media_apply"),
    # Signed HLS playback gate (public — token-verified)
    path("watch/stream/<int:video_id>/", v.hls_stream, name="hls_stream"),
]
