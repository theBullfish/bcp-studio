"""Ingest views — Tailscale record→sync.

A laptop on the user's tailnet records locally; the standalone sync agent
(syncagent/agent.py) watches a folder and uploads new files to `ingest_receive`
over the tailnet, authenticated with a Device api_key. Each arriving file lands
under MEDIA_ROOT/ingest/<device_id>/ and becomes a MediaAsset on the device's
target Project.

Device management (list / create / detail) is staff-facing and behind the studio
RBAC. The upload endpoint itself is csrf-exempt and key-authenticated so it can be
called from a machine that never logs into the web UI.
"""

from __future__ import annotations

import os

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from . import models
from .ingest_models import Device, IngestedFile
from .models import Client, MediaAsset, Project, Role, role_at_least


def _can(user, minimum):
    prof = getattr(user, "profile", None)
    return bool(prof) and role_at_least(prof.role, minimum)


# Map file extension -> MediaAsset.Kind
_EXT_KIND = {
    "mp4": MediaAsset.Kind.VIDEO,
    "mov": MediaAsset.Kind.VIDEO,
    "m4v": MediaAsset.Kind.VIDEO,
    "webm": MediaAsset.Kind.VIDEO,
    "mkv": MediaAsset.Kind.VIDEO,
    "wav": MediaAsset.Kind.AUDIO,
    "mp3": MediaAsset.Kind.AUDIO,
    "aac": MediaAsset.Kind.AUDIO,
    "flac": MediaAsset.Kind.AUDIO,
    "m4a": MediaAsset.Kind.AUDIO,
    "jpg": MediaAsset.Kind.IMAGE,
    "jpeg": MediaAsset.Kind.IMAGE,
    "png": MediaAsset.Kind.IMAGE,
    "gif": MediaAsset.Kind.IMAGE,
    "webp": MediaAsset.Kind.IMAGE,
}

# IngestedFile status -> Bootstrap badge colour
_FILE_BADGE = {
    IngestedFile.Status.RECEIVED: "info",
    IngestedFile.Status.PROCESSED: "success",
    IngestedFile.Status.FAILED: "danger",
}


def _guess_kind(filename: str) -> str:
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return _EXT_KIND.get(ext, MediaAsset.Kind.DOCUMENT)


# ---------------------------------------------------------------------------
# Device management (staff)
# ---------------------------------------------------------------------------


@login_required
def devices(request):
    """Management page: list capture devices + a New device modal."""
    if not _can(request.user, Role.PRODUCER):
        return redirect("studio:dashboard")

    device_list = (
        Device.objects.select_related("client", "target_project")
        .order_by("-created_at")
    )
    return render(
        request,
        "studio/ingest/devices.html",
        {
            "heading": "Capture Devices",
            "pageview": "Studio",
            "devices": device_list,
            "clients": Client.objects.filter(active=True).order_by("name"),
            "projects": Project.objects.select_related("client").order_by("-created_at")[:200],
            "file_badges": _FILE_BADGE,
        },
    )


@login_required
def device_new(request):
    """Create a Device. api_key auto-generates on the model."""
    if request.method != "POST" or not _can(request.user, Role.PRODUCER):
        return redirect("devices")

    name = (request.POST.get("name") or "").strip()
    if not name:
        return redirect("devices")

    client = None
    client_id = request.POST.get("client")
    if client_id:
        client = Client.objects.filter(pk=client_id).first()

    target_project = None
    project_id = request.POST.get("target_project")
    if project_id:
        target_project = Project.objects.filter(pk=project_id).first()

    device = Device.objects.create(
        name=name,
        client=client,
        target_project=target_project,
        auto_run_play=(request.POST.get("auto_run_play") or "").strip(),
    )
    return redirect("device_page", device_id=device.id)


@login_required
def device_page(request, device_id):
    """Device detail: api_key, tailnet host, agent setup instructions, files."""
    if not _can(request.user, Role.PRODUCER):
        return redirect("studio:dashboard")

    device = get_object_or_404(
        Device.objects.select_related("client", "target_project"), pk=device_id
    )
    files = device.files.order_by("-created_at")[:100]

    # Best-effort tailnet host for the copy-paste command; falls back to a
    # placeholder the user swaps for their media server's tailnet IP/host.
    server_host = device.tailnet_host.strip() or "<media-server-tailnet-host>"
    ingest_command = (
        f"python agent.py --server http://{server_host}:8000 "
        f"--key {device.api_key} --watch ~/Recordings"
    )

    return render(
        request,
        "studio/ingest/device_page.html",
        {
            "heading": device.name,
            "pageview": "Studio",
            "device": device,
            "files": files,
            "file_badges": _FILE_BADGE,
            "ingest_command": ingest_command,
        },
    )


# ---------------------------------------------------------------------------
# Ingest API — the endpoint the sync agent uploads to over Tailscale
# ---------------------------------------------------------------------------


@csrf_exempt
def ingest_receive(request):
    """Key-authenticated file upload. Called by syncagent/agent.py over the tailnet.

    Auth: X-Device-Key header (or `key` POST field) -> active Device.api_key.
    Saves the upload under MEDIA_ROOT/ingest/<device_id>/<filename>, records an
    IngestedFile, and creates a MediaAsset on the device's target Project.
    """
    if request.method != "POST":
        return JsonResponse({"error": "method not allowed"}, status=405)

    api_key = request.headers.get("X-Device-Key") or request.POST.get("key")
    if not api_key:
        return JsonResponse({"error": "unauthorized"}, status=401)

    device = Device.objects.filter(api_key=api_key, active=True).first()
    if device is None:
        return JsonResponse({"error": "unauthorized"}, status=401)

    upload = request.FILES.get("file")
    if upload is None:
        return JsonResponse({"error": "no file"}, status=400)

    ingested = None
    try:
        # Sanitize the filename to its basename so a client-supplied path can't
        # escape the per-device ingest directory.
        filename = os.path.basename(upload.name) or "upload.bin"

        dest_dir = os.path.join(settings.MEDIA_ROOT, "ingest", str(device.id))
        os.makedirs(dest_dir, exist_ok=True)
        stored_path = os.path.join(dest_dir, filename)

        size_bytes = 0
        with open(stored_path, "wb") as fh:
            for chunk in upload.chunks():
                fh.write(chunk)
                size_bytes += len(chunk)

        ingested = IngestedFile.objects.create(
            device=device,
            filename=filename,
            size_bytes=size_bytes,
            stored_path=stored_path,
            status=IngestedFile.Status.RECEIVED,
        )

        # Resolve the target project the arriving media should attach to.
        project = device.target_project
        if project is None:
            client = device.client or Client.objects.order_by("id").first()
            if client is None:
                client = Client.objects.create(name="Ingest", slug="ingest")
            project, _ = Project.objects.get_or_create(
                client=client,
                title=f"Inbox — {device.name}",
                defaults={"status": Project.Status.READY},
            )

        # Public URL for the stored file (MEDIA_URL + relative path under MEDIA_ROOT).
        rel_path = os.path.relpath(stored_path, settings.MEDIA_ROOT).replace(os.sep, "/")
        media_url = settings.MEDIA_URL.rstrip("/") + "/" + rel_path

        media = MediaAsset.objects.create(
            project=project,
            kind=_guess_kind(filename),
            label=filename,
            url=media_url,
            status=MediaAsset.Status.READY,
        )

        device.last_seen = timezone.now()
        device.save(update_fields=["last_seen"])

        ingested.status = IngestedFile.Status.PROCESSED
        ingested.save(update_fields=["status"])

        return JsonResponse(
            {"ok": True, "media_id": media.id, "project_id": project.id}
        )
    except Exception as exc:  # noqa: BLE001 — report the failure to the agent
        if ingested is not None:
            ingested.status = IngestedFile.Status.FAILED
            ingested.save(update_fields=["status"])
        return JsonResponse({"ok": False, "error": str(exc)}, status=500)
