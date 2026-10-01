"""Publisher provider base classes.

A *provider* knows how to publish a :class:`studio.models.Post` to one social
platform and (optionally) read back its performance metrics. Concrete
providers live alongside this module (``instagram.py``, ``tiktok.py``, …).

Real providers perform live API calls when the post's ``SocialAccount`` carries
an access token AND the platform's app credentials are present in the
environment. When either is missing they raise :class:`NotConfigured`, which the
package-level :func:`studio.publishers.publish` treats as a signal to fall back
to the :class:`~studio.publishers.mock.MockProvider` so the platform always
works in dev.
"""

from __future__ import annotations


class NotConfigured(Exception):
    """Raised when a real provider lacks credentials/tokens to make a live call.

    This is a *soft* failure: the registry catches it and falls back to the mock
    provider. Any OTHER exception raised from :meth:`Provider.publish` is a hard
    failure and propagates to the caller (so the publish task marks the post
    FAILED with a real reason).
    """


class Provider:
    """Base class for a single-platform publisher.

    Subclasses set :attr:`platform` and override :meth:`publish` (and optionally
    :meth:`metrics`).
    """

    #: ``studio.models.Platform`` value this provider handles.
    platform: str | None = None

    def publish(self, post) -> dict:
        """Publish ``post`` and return ``{"url": <permalink>, "id": <remote id>}``.

        Raise :class:`NotConfigured` when the provider cannot make a live call.
        """
        raise NotImplementedError

    def metrics(self, post) -> dict | None:
        """Return a metrics dict for ``post`` (fields matching ``PostMetric``).

        Base implementation is intentionally unimplemented; the registry falls
        back to the mock provider for platforms that do not read metrics.
        """
        raise NotImplementedError
