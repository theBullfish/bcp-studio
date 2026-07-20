"""Storage-backed uploads, signed HLS playback gate, and the quick-finish editor.

These views work against ``django.core.files.storage.default_storage`` so they
behave identically on local FileSystemStorage (dev) and S3/R2 (prod). Every
media write and URL goes through ``default_storage``; nothing assumes a local
path. ffmpeg-less environments still create rows and render pages.
"""

from __future__ import annotations

import os

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.storage import default_storage
from django.http import (
    HttpResponseForbidden,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import models, signing
from .models import Role, role_at_least

# Map file extensions to MediaAsset.Kind.
_EXT_KIND = {
    ".mp4": "VIDEO", ".mov": "VIDEO", ".mkv": "VIDEO", ".webm": "VIDEO", ".avi": "VIDEO",
    ".m4v": "VIDEO",
    ".mp3": "AUDIO", ".wav": "AUDIO", ".aac": "AUDIO", ".flac": "AUDIO", ".m4a": "AUDIO",
    ".ogg": "AUDIO",
    ".jpg": "IMAGE", ".jpeg": "IMAGE", ".png": "IMAGE", ".gif": "IMAGE", ".webp": "IMAGE",
    ".pdf": "DOCUMENT", ".txt": "DOCUMENT", ".srt": "DOCUMENT", ".vtt": "DOCUMENT",
    ".doc": "DOCUMENT", ".docx": "DOCUMENT",
}


def _can(user, minimum) -> bool:
    prof = getattr(user, "profile", None)
    return bool(prof) and role_at_least(prof.role, minimum)


def _guess_kind(name: str) -> str:
    return _EXT_KIND.get(os.path.splitext(name or "")[1].lower(), "VIDEO")


def _is_xhr(request) -> bool:
    return request.headers.get("x-requested-with") == "XMLHttpRequest"


def _stored_url(saved_name: str) -> str:
    """Best-effort public/signed URL for a stored object; fall back to the key."""
    try:
        return default_storage.url(saved_name)
    except Exception:
        return saved_name


# ---------------------------------------------------------------------------
# Uploads
# ---------------------------------------------------------------------------


@login_required
def media_upload(request, project_id):
    project = get_object_or_404(models.Project.objects.select_related("client"), id=project_id)

    if not _can(request.user, Role.PRODUCER):
        if _is_xhr(request):
            return JsonResponse({"error": "forbidden"}, status=403)
        messages.error(request, "You don't have permission to upload media.")
        return redirect("studio:project_detail", project_id=project.id)

    if request.method == "POST":
        upload = request.FILES.get("file")
        if not upload:
            if _is_xhr(request):
                return JsonResponse({"error": "no file"}, status=400)
            messages.error(request, "No file was uploaded.")
            return redirect("studio:media_upload", project_id=project.id)

        name = os.path.basename(upload.name)
        # default_storage assigns a unique name if one already exists.
        saved_name = default_storage.save(f"uploads/{project.id}/{name}", upload)

        asset = models.MediaAsset.objects.create(
            project=project,
            uploader=request.user,
            kind=_guess_kind(name),
            label=name,
            url=_stored_url(saved_name),
            status=models.MediaAsset.Status.READY,
        )

        if _is_xhr(request):
            return JsonResponse(
                {"ok": True, "media_id": asset.id, "label": asset.label, "url": asset.url}
            )
        messages.success(request, f"Uploaded {name}.")
        return redirect("studio:project_detail", project_id=project.id)

    return render(
        request,
        "studio/media/upload.html",
        {"heading": f"Upload — {project.title}", "pageview": "Projects", "project": project},
    )


# ---------------------------------------------------------------------------
# Quick-finish editor (trim + caption)
# ---------------------------------------------------------------------------


@login_required
def media_edit(request, media_id):
    media = get_object_or_404(
        models.MediaAsset.objects.select_related("project", "project__client"), id=media_id
    )
    if not _can(request.user, Role.EDITOR):
        messages.error(request, "You don't have permission to edit media.")
        return redirect("studio:project_detail", project_id=media.project_id)

    return render(
        request,
        "studio/media/edit.html",
        {
            "heading": f"Finish — {media.label}",
            "pageview": "Projects",
            "media": media,
            "project": media.project,
        },
    )


@login_required
@require_POST
def media_apply(request, media_id):
    media = get_object_or_404(models.MediaAsset, id=media_id)
    if not _can(request.user, Role.EDITOR):
        messages.error(request, "You don't have permission to edit media.")
        return redirect("studio:project_detail", project_id=media.project_id)

    try:
        start = float(request.POST.get("start") or 0)
    except (TypeError, ValueError):
        start = 0.0
    try:
        end = float(request.POST.get("end") or 0)
    except (TypeError, ValueError):
        end = 0.0
    caption = (request.POST.get("caption") or "").strip()

    from .editing import trim_media_task

    trim_media_task.delay(media_id, start, end, caption)

    messages.success(request, "Rendering your edit — the finished clip will appear on the project.")
    return redirect("studio:project_detail", project_id=media.project_id)


# ---------------------------------------------------------------------------
# Signed HLS playback gate
# ---------------------------------------------------------------------------


def hls_stream(request, video_id):
    """Public gate: verify the ?t= token, then redirect to the real media URL.

    This is what ``signing.signed_hls_url`` points at on local storage. On S3/R2
    the signed URL bypasses this and hits the object directly.
    """
    video = get_object_or_404(models.Video, id=video_id)
    token = request.GET.get("t", "")

    if not signing.verify_hls_token(video_id, token, max_age=getattr(settings, "AWS_QUERYSTRING_EXPIRE", 3600)):
        return HttpResponseForbidden("Invalid or expired playback token.")

    hls_path = video.hls_path or ""
    if hls_path:
        if getattr(settings, "AWS_STORAGE_BUCKET_NAME", ""):
            target = _stored_url(hls_path)
        elif hls_path.startswith("http://") or hls_path.startswith("https://"):
            target = hls_path
        elif os.path.isabs(hls_path):
            # Local absolute path under MEDIA_ROOT -> serve via MEDIA_URL.
            media_root = str(getattr(settings, "MEDIA_ROOT", ""))
            rel = os.path.relpath(hls_path, media_root) if media_root and hls_path.startswith(media_root) else None
            target = f"{settings.MEDIA_URL}{rel}" if rel and not rel.startswith("..") else _stored_url(hls_path)
        else:
            target = _stored_url(hls_path)
    else:
        target = video.source_url or ""

    if not target:
        return HttpResponseForbidden("No playable source for this video.")
    return redirect(target)
