"""Shared fixtures for the BCP Studio test suite.

Keep fixtures lightweight and deterministic. `seeded` runs the real
`seed_studio` management command for tests that want the full demo dataset;
most tests build only the minimal objects they need via the factory fixtures.
"""

from __future__ import annotations

import pytest
from django.contrib.auth.models import User

from studio import models


@pytest.fixture
def make_user(db):
    """Factory: create a User with a Profile of the given role.

    A Profile is auto-created by the post_save signal; we just set its role.
    """

    def _make(username="tester", role=models.Role.OWNER, password="pw12345", **kwargs):
        user = User.objects.create_user(username=username, password=password, **kwargs)
        prof = user.profile  # auto-created by signal
        prof.role = role
        prof.save()
        return user

    return _make


@pytest.fixture
def client_logged_in(client, make_user):
    """Factory: return a Django test Client logged in as a user of `role`.

    Uses force_login so we don't depend on allauth's login form.
    """

    def _login(role=models.Role.OWNER, username=None):
        uname = username or f"user_{role.lower()}"
        user = make_user(username=uname, role=role)
        client.force_login(user)
        return client

    return _login


@pytest.fixture
def basic_client(db):
    """A Client with an attached BrandKit."""
    c = models.Client.objects.create(name="Test Client", slug="test-client")
    models.BrandKit.objects.create(client=c, hashtags_csv="#one, #two ,, #three")
    return c


@pytest.fixture
def basic_project(basic_client, make_user):
    owner = make_user(username="proj_owner", role=models.Role.PRODUCER)
    return models.Project.objects.create(
        client=basic_client, owner=owner, title="Test Project"
    )


@pytest.fixture
def seeded(db):
    """Run the real seed_studio command to populate the full demo dataset."""
    from django.core.management import call_command

    call_command("seed_studio")
