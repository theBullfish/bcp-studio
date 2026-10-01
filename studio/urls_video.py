"""URL patterns for the paid video platform (public watch + staff management).

Plain urlpatterns (no app_name) — included by the project root urls under the
same 'studio' namespace as the rest of the app, so {% url 'studio:watch_home' %}
etc. resolve.
"""

from django.urls import path

from . import views_video as v

urlpatterns = [
    # --- Public: watch ---
    path("watch/", v.watch_home, name="watch_home"),
    path("watch/c/<slug:slug>/", v.watch_channel, name="watch_channel"),
    path("watch/v/<int:video_id>/", v.watch_video, name="watch_video"),
    path("watch/subscribe/<int:plan_id>/", v.subscribe, name="subscribe"),
    path("watch/subscribed/", v.sub_success, name="sub_success"),
    # --- Staff: manage ---
    path("videos/manage/", v.video_manage, name="video_manage"),
    path("videos/manage/new/", v.video_new, name="video_new"),
    path("videos/manage/<int:video_id>/transcode/", v.video_transcode, name="video_transcode"),
]
