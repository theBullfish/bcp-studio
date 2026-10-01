"""Ingest URLs — the Tailscale record→sync pipeline.

Plain urlpatterns (NO app_name) so these names resolve globally: the device
management pages plus the key-authenticated upload endpoint the sync agent hits.
"""

from django.urls import path

from . import views_ingest as v

urlpatterns = [
    path("devices/", v.devices, name="devices"),                          # staff: list/manage devices
    path("devices/new/", v.device_new, name="device_new"),                # POST create device
    path("devices/<int:device_id>/", v.device_page, name="device_page"),  # detail + agent setup + files
    path("ingest/", v.ingest_receive, name="ingest_receive"),             # API: POST file upload (csrf-exempt, key auth)
]
