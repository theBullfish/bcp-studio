"""Ingest models — the Tailscale record→sync pipeline.

A laptop runs the sync agent (syncagent/agent.py) on your tailnet. It uploads
recordings to the server ingest endpoint authenticated with a Device key. Each
arriving file becomes a MediaAsset on the device's target Project.
"""

import secrets

from django.db import models

from .models import Client, Project


def _gen_key() -> str:
    return "bcpk_" + secrets.token_urlsafe(24)


class Device(models.Model):
    """A trusted capture device (e.g. your laptop) allowed to push media in."""

    name = models.CharField(max_length=200)
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True)
    # New arrivals land on this project (or a per-day project if blank).
    target_project = models.ForeignKey(
        Project, on_delete=models.SET_NULL, null=True, blank=True, related_name="ingest_devices"
    )
    api_key = models.CharField(max_length=80, unique=True, default=_gen_key)
    tailnet_host = models.CharField(max_length=200, blank=True)
    auto_run_play = models.CharField(max_length=60, blank=True)  # play key to auto-run on arrival
    active = models.BooleanField(default=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class IngestedFile(models.Model):
    class Status(models.TextChoices):
        RECEIVED = "RECEIVED", "Received"
        PROCESSED = "PROCESSED", "Processed"
        FAILED = "FAILED", "Failed"

    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name="files")
    filename = models.CharField(max_length=500)
    size_bytes = models.BigIntegerField(default=0)
    checksum = models.CharField(max_length=128, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.RECEIVED)
    stored_path = models.CharField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.filename
