install:
	poetry install

dev:
	poetry run uvicorn src.main:app --reload --port 8000

test:
	poetry run pytest --cov=src --cov-report=term-missing

lint:
	poetry run ruff check src tests

format:
	poetry run ruff format src tests

typecheck:
	poetry run mypy src

pre-commit:
	poetry run pre-commit install

migrate:
	poetry run alembic upgrade head

migrate-create:
	poetry run alembic revision --autogenerate -m "$(message)"

docker-build:
	docker compose build

docker-up:
	docker compose up -d

docker-down:
	docker compose down
