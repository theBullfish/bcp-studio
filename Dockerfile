FROM python:3.11-slim

# ffmpeg lets the AI plays render real media; without it they plan outputs only.
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

EXPOSE 8000
# Migrate + seed on first boot, then serve.
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py seed_studio && gunicorn skote.wsgi:application --bind 0.0.0.0:8000"]
