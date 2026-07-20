# BCP Studio — CLAUDE.md

## What this is
AI media production & social publishing platform for Balls and Chunk Productions.
Record a bit → AI plays cut it into every format → finish → approve → auto-post → track.
Built ON the **Skote** Django Bootstrap admin template — USE its real components, don't reskin.

## Stack & layout
- Django 4.2, allauth auth, Skote front-end. Postgres in prod / SQLite in dev.
- `skote/` — Django project package (settings, root urls). Keep the package name.
- `studio/` — our app: `models.py` (whole data model), `views.py` (screens),
  `services.py` (AI plays + caption gen), `admin.py` (back office), `urls.py`,
  `management/commands/seed_studio.py`, `templatetags/studio_extras.py`.
- `templates/studio/*` — our pages, each `{% extends 'partials/base.html' %}`.
- `templates/partials/sidebar.html` — our nav (customized).
- `static/` — Skote compiled libs (ApexCharts, DataTables, FullCalendar, chat).
- `docs/TEMPLATE_SPEC.md` — how to build pages on Skote's components. Read before adding UI.

## Conventions
- Deep CRUD = Django admin (everything registered). Day-to-day flow = studio views.
- RBAC: `role_at_least()` in models; `_can(user, Role.X)` in views. 7 roles.
- Analytics/revenue/pay are INTERNAL only — behind login, never public.
- AI plays/captions in `studio/services.py`; degrade gracefully (no ffmpeg / no API key).

## Commands
```bash
python manage.py migrate
python manage.py seed_studio        # demo data + logins
python manage.py runserver
python manage.py createsuperuser
```

## Login (seed)
owner / chunk1234  (email owner@ballsandchunk.com). Six accounts, one per role.
