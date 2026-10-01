# Deployment

The app runs zero-config in dev (SQLite, synchronous tasks, local storage) and
scales to production by setting environment variables — no code changes.

## Environment matrix

| Concern | Dev (default) | Production |
|---|---|---|
| Database | SQLite | `DATABASE_URL=postgres://…` |
| Background jobs | eager (inline) | `CELERY_BROKER_URL=redis://…` + worker + beat |
| Media storage | local `MEDIA_ROOT` | `AWS_STORAGE_BUCKET_NAME` (+ keys / `AWS_S3_ENDPOINT_URL` for R2) |
| Static | Django dev server | WhiteNoise (compressed), `collectstatic` at build |
| Payments | mock (no key) | `STRIPE_SECRET_KEY` + `STRIPE_WEBHOOK_SECRET` |
| Captions | template fallback | `ANTHROPIC_API_KEY` |
| Publishing | mock provider | per-platform OAuth creds (`META_*`, `TIKTOK_*`, `YOUTUBE_*`, `X_*`) |
| Security | `DJANGO_DEBUG=1` | `DJANGO_DEBUG=0` → HSTS, SSL redirect, secure cookies auto-on |

## Quick production bring-up (Docker Compose)

```bash
cp .env.example .env     # fill DJANGO_SECRET_KEY, DATABASE handled by compose, Stripe, etc.
docker compose up --build -d
```

Compose brings up **db** (Postgres), **redis**, **web** (gunicorn), **worker**
(Celery), and **beat** (scheduler). The web image runs migrations + seed on first
boot and serves static via WhiteNoise.

## Manual / VM

```bash
pip install -r requirements.txt
export DJANGO_DEBUG=0 DJANGO_SECRET_KEY=... DATABASE_URL=... CELERY_BROKER_URL=redis://...
python manage.py migrate
python manage.py collectstatic --noinput
gunicorn skote.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120
# separate processes:
celery -A skote worker -l info
celery -A skote beat -l info
```

## Scheduler (beat) jobs
- `publish_due_posts` — every minute, publishes SCHEDULED posts whose time has come.
- `poll_all_metrics` — every 15 min, refreshes performance metrics for published posts.

## Secrets
Use SOPS + age (as in the GritBox/eaas repos) or your platform's secret manager.
Never commit real keys. `*.key` and `.env` are gitignored; `.env.example` documents
every variable.

## Notes
- Stripe webhook endpoint: `POST /shop/webhook/` (set the signing secret in prod).
- HLS video: transcoded to `HLS_ROOT` (or S3) and served via signed/expiring URLs.
- Flip `ACCOUNT_EMAIL_VERIFICATION` back to `"mandatory"` and configure SMTP for
  real signups.
