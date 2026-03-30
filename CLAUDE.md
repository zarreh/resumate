# ResuMate — Claude Code Context

## Implementation Plan

The detailed session-by-session implementation plan is at:
**[docs/implementation-plan.md](docs/implementation-plan.md)**

Read this at the start of every session. It contains:
- All ~38 sub-phases with acceptance criteria, file lists, and code patterns
- Critical path and dependency graph
- Risk register
- Retrospectives (updated after each completed sub-phase)

## Project Conventions

- All markdown and documentation files live in `docs/`. Exception: `README.md` files stay at standard locations.
- No `Co-Authored-By` lines in git commits.

## Tech Stack

- **Backend:** FastAPI + LangGraph + PostgreSQL (pgvector) + SQLAlchemy async + Alembic
- **Frontend:** Next.js (App Router) + TypeScript + Tailwind + shadcn/ui
- **AI:** LangChain (OpenAI / Anthropic) — config driven via `backend/config/llm.yaml`
- **PDF:** LaTeX via `tectonic` + Jinja2 (custom delimiters: `\VAR{}`, `\BLOCK{}`)
- **Auth:** JWT (access 30min + refresh 7d, stored hashed in DB)
- **Streaming:** WebSocket per session, token passed as query param

## Repo Structure

```
resumate/
├── CLAUDE.md               ← you are here
├── docs/                   ← all documentation
│   └── implementation-plan.md
├── backend/                ← FastAPI app (Poetry, Python 3.12)
│   ├── src/
│   ├── tests/
│   ├── config/
│   └── templates/latex/
└── frontend/               ← Next.js app (added in phase 1.5)
```

## Current Progress

> **Rule:** After completing any sub-phase, mark it `[x]` here immediately. This checklist is the canonical at-a-glance status — keep it in sync with `docs/implementation-plan.md`.

- [x] 1.1 — Project Scaffolding (backend structure, pyproject.toml, Makefile, config)
- [x] 1.2 — Docker Compose Setup
- [x] 1.3 — Database Schema & Migrations
- [x] 1.4 — FastAPI Skeleton + Auth
- [x] 1.5 — Next.js Frontend Scaffolding
- [x] 1.6 — WebSocket Streaming Infrastructure
