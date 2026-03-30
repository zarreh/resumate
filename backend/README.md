# ResuMate Backend

AI-powered resume tailoring API built with FastAPI, LangGraph, and PostgreSQL.

## Setup

```bash
cp .env.example .env
# Fill in your API keys and database URL

make install
make pre-commit
make migrate
make dev
```

## Development

```bash
make test        # Run tests with coverage
make lint        # Lint with ruff
make format      # Format with ruff
make typecheck   # Type check with mypy
```

## Docker

```bash
make docker-up   # Start all services
make docker-down # Stop all services
```
