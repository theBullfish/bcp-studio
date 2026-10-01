"""URL patterns for the OAuth channel-connect flow.

Plain urlpatterns (no ``app_name``) so the names resolve in the ``studio:``
namespace when included from the studio URLconf::

    path("", include("studio.urls_publish")),
"""

from django.urls import path

from . import views_publish as v

urlpatterns = [
    path(
        "connect/<int:client_id>/<str:platform>/start/",
        v.connect_start,
        name="connect_start",
    ),
    path(
        "connect/<str:platform>/callback/",
        v.connect_callback,
        name="connect_callback",
    ),
]
