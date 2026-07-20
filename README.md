# Balls &amp; Chunk Studio

An AI media production &amp; social publishing platform for **Balls and Chunk Productions**
(and resellable per-client). The core loop:

> **Record a bit → hand it to the server → AI "plays" cut it into every format →
> a person quickly finishes the edit → approvers sign off → it auto-posts on schedule,
> with all the tracking data attached.**

Built on the **Skote** Django admin template — it uses Skote's real component library
(ApexCharts, DataTables, FullCalendar, chat UI, Bootstrap 5) rather than reskinning it.

## What's in the box

- **AI Plays** — pre-built recipes that decompose one source into every deliverable
  (vertical reels, squares, stories, audiograms, quote cards, thumbnails, transcripts…).
- **Auto-copy** — captions written from a one-line summary, brand-tone aware
  (Claude-powered when `ANTHROPIC_API_KEY` is set, deterministic templates otherwise).
- **Clients / brands** — each client has its own logos, colors, fonts and voice.
- **Scheduling &amp; posting** — manual or automatic, per platform, on a calendar.
- **Two calendar views** — a focused *your release dates* view and a company-wide view.
- **Approvals** — multi-level roles; a couple of people sign off before anything posts.
- **Private tracking** — revenue, pay, post performance, trends/news — internal only.
- **Accounts &amp; messaging** — profiles, roles, in-app messaging, notifications.
- **Back office** — full Django admin CRUD over every model for Owners/Admins.

## Stack

- **Django 4.2** — models, views, auth (allauth), admin. One codebase.
- **Skote** Bootstrap 5 admin template — the entire front-end (`templates/`, `static/`).
- **PostgreSQL** in production, **SQLite** for zero-config local dev.
- **AI plays + captions** run in `studio/services.py` (ffmpeg + Claude), Celery-ready.

## Quick start (local, zero config)

```bash
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_studio        # demo data + login accounts
python manage.py runserver
# open http://127.0.0.1:8000/
```

**Login:** `owner` / `chunk1234` (or email `owner@ballsandchunk.com`).
Six seeded accounts, one per role. The owner is a Django superuser, so
**Back Office** (`/admin/`) works too.

## Roles

`OWNER → ADMIN → PRODUCER → EDITOR → APPROVER → CONTRIBUTOR → VIEWER`
Capabilities are enforced in `studio/models.py` (`role_at_least`) and checked in views.

## Layout

```
bcp-studio/
├── manage.py
├── requirements.txt
├── skote/                 # Django project (settings, root urls)  ← template's project pkg
├── studio/                # our app: models, views, services, admin, seed, urls
│   ├── models.py          # the whole data model
│   ├── views.py           # every screen
│   ├── services.py        # AI plays engine + caption generation
│   ├── admin.py           # back-office CRUD
│   └── management/commands/seed_studio.py
├── templates/             # Skote templates + templates/studio/* (our pages)
├── static/                # Skote compiled assets (ApexCharts, DataTables, FullCalendar…)
├── layout/ pages/         # Skote's own apps (auth forms, layout demos) — kept
└── docs/TEMPLATE_SPEC.md  # how our pages plug into Skote's components
```

## Production notes

- Set `DEBUG=False`, a real `SECRET_KEY`, `ALLOWED_HOSTS`, and a Postgres `DATABASE_URL`.
- Switch `ACCOUNT_EMAIL_VERIFICATION` back to `"mandatory"` and configure SMTP.
- Move the AI plays to a Celery worker; wire real platform-publish providers.
- See `ROADMAP.md` for what's built vs. next.
