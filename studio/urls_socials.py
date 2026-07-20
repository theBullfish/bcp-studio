"""URL patterns for the SOCIALS & DISTRIBUTION management module.

Plain urlpatterns (no app_name) so these names resolve in the default
namespace when included. Wire into the project with:

    path("", include("studio.urls_socials")),
"""

from django.urls import path

from . import views_socials as v

urlpatterns = [
    path("distribution/", v.distribution, name="distribution"),
    path("distribution/<int:client_id>/", v.dist_client, name="dist_client"),
    path(
        "distribution/<int:client_id>/authorize/",
        v.channel_authorize,
        name="channel_authorize",
    ),
    path("distribution/<int:client_id>/rule/new/", v.rule_new, name="rule_new"),
    path(
        "distribution/rule/<int:rule_id>/delete/",
        v.rule_delete,
        name="rule_delete",
    ),
    path("distribution/<int:client_id>/profile/", v.profile_save, name="profile_save"),
]
