"""Celery application for background jobs.

With no CELERY_BROKER_URL set, tasks run eagerly (synchronously) so the app
needs no Redis in dev. In production, run a worker + beat against Redis.
"""

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "skote.settings")

app = Celery("bcp")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
