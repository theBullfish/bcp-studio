FROM python:3.11-slim

# ffmpeg powers the AI plays, HLS transcode, and the quick-finish editor.
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DJANGO_DEBUG=0
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Collect static for WhiteNoise (needs a key; DEBUG off is fine here).
RUN DJANGO_SECRET_KEY=build python manage.py collectstatic --noinput

EXPOSE 8000
# Migrate + seed on first boot, then serve via gunicorn.
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py seed_studio && gunicorn skote.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 120"]
