PYTHON ?= python3
ALEMBIC ?= $(PYTHON) -m alembic

install:
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -e .[dev]

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check .

format:
	$(PYTHON) -m ruff format .

run:
	$(PYTHON) -m polymarket_scalper

record:
	$(PYTHON) -m polymarket_scalper record-once

health:
	$(PYTHON) -m polymarket_scalper health

audit:
	$(PYTHON) -m polymarket_scalper audit

db-up:
	docker compose up -d postgres

db-down:
	docker compose stop postgres

db-migrate:
	$(ALEMBIC) -x db_url=$$DATABASE_URL upgrade head

docker-build:
	docker compose build

docker-up:
	docker compose up app

docker-record:
	docker compose run --rm recorder

docker-logs:
	docker compose logs -f recorder postgres

docker-down:
	docker compose down

docker-test:
	docker compose run --rm test
