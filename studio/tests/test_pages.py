"""Smoke tests: main pages render for an authenticated OWNER; public pages for all."""

import pytest

from studio import models

pytestmark = pytest.mark.django_db


STAFF_PAGES = [
    "/",
    "/posts/",
    "/analytics/",
    "/calendar/",
    "/clients/",
    "/team/",
    "/messages/",
    "/approvals/",
    "/projects/",
    "/plays/",
    "/store/manage/",
    "/videos/manage/",
    "/distribution/",
    "/devices/",
]

PUBLIC_PAGES = ["/shop/", "/watch/"]


@pytest.mark.parametrize("path", STAFF_PAGES)
def test_owner_can_load_staff_pages(seeded, client_logged_in, path):
    c = client_logged_in(models.Role.OWNER)
    resp = c.get(path)
    assert resp.status_code == 200, f"{path} -> {resp.status_code}"


@pytest.mark.parametrize("path", PUBLIC_PAGES)
def test_public_pages_load_anonymously(seeded, client, path):
    resp = client.get(path)
    assert resp.status_code == 200, f"{path} -> {resp.status_code}"


def test_anonymous_dashboard_redirects_to_login(client):
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/login" in resp["Location"] or "account" in resp["Location"].lower()
