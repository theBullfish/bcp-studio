from django.urls import include, path

from . import views

app_name = "studio"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),

    # Clients / brands
    path("clients/", views.clients_list, name="clients"),
    path("clients/create/", views.client_create, name="client_create"),
    path("clients/<int:client_id>/", views.client_detail, name="client_detail"),
    path("clients/<int:client_id>/brand-kit/", views.brand_kit_update, name="brand_kit_update"),
    path("clients/<int:client_id>/social/", views.social_add, name="social_add"),

    # Projects & media
    path("projects/", views.projects_list, name="projects"),
    path("projects/create/", views.project_create, name="project_create"),
    path("projects/<int:project_id>/", views.project_detail, name="project_detail"),
    path("projects/<int:project_id>/media/", views.media_add, name="media_add"),
    path("projects/<int:project_id>/run-play/", views.play_run, name="play_run"),

    # Plays
    path("plays/", views.plays_list, name="plays"),

    # Posts / schedule
    path("posts/", views.posts_list, name="posts"),
    path("posts/compose/", views.post_compose, name="post_compose"),
    path("posts/caption/", views.caption_generate, name="caption_generate"),
    path("posts/<int:post_id>/", views.post_detail, name="post_detail"),
    path("posts/<int:post_id>/update/", views.post_update, name="post_update"),
    path("posts/<int:post_id>/submit/", views.post_submit_review, name="post_submit_review"),
    path("posts/<int:post_id>/publish/", views.post_publish, name="post_publish"),

    # Approvals
    path("approvals/", views.approvals_list, name="approvals"),
    path("approvals/<int:approval_id>/decide/", views.approval_decide, name="approval_decide"),

    # Calendar
    path("calendar/", views.calendar, name="calendar"),
    path("calendar/events/", views.calendar_events, name="calendar_events"),

    # Analytics
    path("analytics/", views.analytics, name="analytics"),

    # Messaging
    path("messages/", views.messages_view, name="messages"),
    path("messages/<int:conversation_id>/send/", views.message_send, name="message_send"),

    # Team
    path("team/", views.team_list, name="team"),
    path("team/<int:user_id>/update/", views.team_update, name="team_update"),

    # New pillars (self-contained modules; names resolve under the studio namespace)
    path("", include("studio.urls_store")),
    path("", include("studio.urls_video")),
    path("", include("studio.urls_socials")),
    path("", include("studio.urls_ingest")),
    # Phase 4: OAuth connect + storage uploads / editor / signed video streaming
    path("", include("studio.urls_publish")),
    path("", include("studio.urls_media")),
]
