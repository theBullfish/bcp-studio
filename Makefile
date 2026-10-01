.PHONY: dev migrate seed test lint worker beat run docker up collectstatic check

VENV = . .venv/bin/activate &&

dev: migrate seed run

migrate:
	$(VENV) python manage.py migrate

seed:
	$(VENV) python manage.py seed_studio

run:
	$(VENV) python manage.py runserver

worker:
	$(VENV) celery -A skote worker -l info

beat:
	$(VENV) celery -A skote beat -l info

test:
	$(VENV) pytest

lint:
	$(VENV) ruff check studio skote syncagent

check:
	$(VENV) python manage.py check && $(VENV) python manage.py makemigrations --check --dry-run

collectstatic:
	$(VENV) python manage.py collectstatic --noinput

up:
	docker compose up --build
