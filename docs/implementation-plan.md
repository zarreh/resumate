# ResuMate — Detailed Implementation Plan

## Context

This plan provides a session-by-session implementation blueprint for the ResuMate project based on PLAN_v2.md. The project is greenfield (no code exists). Each sub-phase is sized for a single Claude Code session. Three sub-phases have been split from the original plan to keep session scope manageable, bringing the total to ~38 sub-phases.

**Key splits from the original plan:**
- 2.2 → 2.2a (LLM Config Infrastructure) + 2.2b (Resume Parsing) — LLM config is foundational infra
- 4.3 → 4.3a (Full Draft Display) + 4.3b (Per-Bullet Approval Loop) — Gate 3 is the most complex UI
- 4.5 (WebSocket) → moved to 1.6 — it's foundational infra needed by Phases 4-5

---

## Project Conventions

- **All markdown and documentation files** (plans, specs, ADRs, notes) live in `docs/` at the repo root. The only exception is `README.md` files, which stay at their standard locations (`/README.md`, `backend/README.md`, `frontend/README.md`).
- The existing `PLAN.md`, `PLAN_v2.md`, and `rough_plan.md` files have been moved to `docs/`.

---

## Plan Maintenance Rule

**After completing each sub-phase**, you MUST:

### 1. Update `CLAUDE.md`
Mark the completed sub-phase with `[x]` in the **Current Progress** checklist in `CLAUDE.md`. This is mandatory — it keeps the top-level status visible at a glance without reading the full plan.

### 2. Update this plan
Review and update `docs/implementation-plan.md` if:
1. **Execution diverged from the plan** — document what actually happened vs. what was planned (different file structure, different packages, different API signatures, etc.)
2. **New details emerged** — if implementing the current sub-phase revealed missing details, gotchas, or dependencies for future sub-phases, add them now while the context is fresh
3. **Scope changed** — if a sub-phase turned out larger/smaller than expected, split or merge future sub-phases accordingly
4. **Dependencies shifted** — if implementation uncovered new inter-phase dependencies, update the critical path and dependency graph

**Format for updates:** Add a `### Retrospective` section at the end of each completed sub-phase with:
- What changed from the plan and why
- New gotchas discovered
- Adjustments needed for upcoming sub-phases

This keeps the plan as a **living document** that stays accurate, rather than a stale spec that drifts from reality.

---

## Critical Path

```
1.1 → 1.2 → 1.3 → 1.4 → 2.2a → 2.1 → 2.2b → 2.4 → 3.1 → 3.2 → 4.1 → 4.2 → 4.3a → 4.4
                            ↘ 1.5 → 1.6 → 2.3, 3.3, etc. (frontend parallel track)
```

Frontend (1.5+) and backend can advance in parallel after 1.4.

---

## Risk Register

| Risk | Impact | Mitigation |
|---|---|---|
| LaTeX compilation in Docker | Blocks PDF output | Use `tectonic` (auto-downloads packages); test early in 1.2 |
| Jinja2 delimiters conflict with LaTeX `{}` | Broken templates | Use `\VAR{}`, `\BLOCK{}` delimiters from Jinja2-LaTeX conventions |
| WebSocket + LangGraph streaming integration | Complex wiring | Dedicate sub-phase 1.6 solely to this; prototype early |
| LLM structured output reliability | Parsing failures | Use Pydantic + retry with validation; mock in tests |
| pgvector extension availability | Blocks embeddings | Use official `pgvector/pgvector:pg16` Docker image |
| Frontend complexity for React-inexperienced owner | Maintenance burden | Thorough comments, shadcn/ui, TypeScript strict mode |

---

## Phase 1: Foundation & Infrastructure

### 1.1 — Project Scaffolding

**Dependencies:** None
**Complexity:** Small

**Files to create:**
```
backend/
├── pyproject.toml
├── Makefile
├── .env.example
├── .ruff.toml
├── mypy.ini
├── .pre-commit-config.yaml
├── .gitignore
├── README.md
├── src/
│   ├── __init__.py
│   ├── api/
│   │   └── __init__.py
│   ├── agents/
│   │   └── __init__.py
│   ├── models/
│   │   └── __init__.py
│   ├── services/
│   │   └── __init__.py
│   ├── schemas/
│   │   └── __init__.py
│   └── core/
│       ├── __init__.py
│       └── config.py           # Pydantic Settings base
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   └── unit/
│       └── __init__.py
├── config/
│   └── llm.yaml.example
└── templates/
    └── latex/
        └── .gitkeep
```

**Key packages (pyproject.toml):**
```
python = "^3.12"
fastapi = "^0.115"
uvicorn = {extras = ["standard"]}
sqlalchemy = {extras = ["asyncio"], version = "^2.0"}
alembic = "^1.14"
asyncpg = "^0.30"
pydantic = "^2.10"
pydantic-settings = "^2.7"
python-jose = {extras = ["cryptography"]}
passlib = {extras = ["bcrypt"]}
python-multipart = "*"
langchain-core = "^0.3"
langchain-openai = "^0.3"
langchain-anthropic = "^0.3"
langgraph = "^0.3"
pgvector = "^0.3"
pymupdf = "^1.25"
python-docx = "^1.1"
jinja2 = "^3.1"
httpx = "^0.28"
pyyaml = "^6.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
pytest-asyncio = "^0.24"
pytest-cov = "^6.0"
ruff = "^0.9"
mypy = "^1.14"
pre-commit = "^4.0"
```

**Makefile targets:**
- `install`: `poetry install`
- `dev`: `poetry run uvicorn src.main:app --reload --port 8000`
- `test`: `poetry run pytest --cov=src --cov-report=term-missing`
- `lint`: `poetry run ruff check src tests`
- `format`: `poetry run ruff format src tests`
- `typecheck`: `poetry run mypy src`
- `pre-commit`: `poetry run pre-commit install`

**`src/core/config.py`:**
```python
class Settings(BaseSettings):
    database_url: str
    secret_key: str
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    llm_config_path: str = "config/llm.yaml"
    cors_origins: list[str] = ["http://localhost:3000"]
    model_config = SettingsConfigDict(env_file=".env")
```

**Acceptance criteria:**
- `make install` succeeds
- `make lint && make format && make typecheck` all pass (empty project)
- `pre-commit install` works
- Project structure matches the layout above

---

### 1.2 — Docker Compose Setup

**Dependencies:** 1.1
**Complexity:** Small-Medium

**Files to create:**
```
backend/Dockerfile
docker-compose.yml          # At repo root
scripts/init-db.sh
```

**`docker-compose.yml` services:**
- `backend`: Python + tectonic (for LaTeX), mounts `./backend` for dev
- `postgres`: `pgvector/pgvector:pg16`, port 5432, volume for data persistence
- `frontend`: Node.js (added in 1.5, placeholder here)

**`Dockerfile` key steps:**
```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y curl
RUN curl --proto '=https' --tlsv1.2 -fsSL https://drop-sh.fullyjustified.net | sh
# tectonic is now available for LaTeX compilation
COPY pyproject.toml poetry.lock ./
RUN pip install poetry && poetry install --no-root
COPY . .
CMD ["poetry", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

**`scripts/init-db.sh`:**
```bash
psql -U $POSTGRES_USER -d $POSTGRES_DB -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

**Makefile additions:** `docker-build`, `docker-up`, `docker-down`

**Acceptance criteria:**
- `make docker-up` starts backend + postgres
- Backend connects to postgres (health check endpoint returns 200)
- `docker exec backend tectonic --version` works
- pgvector extension is installed (`SELECT * FROM pg_extension WHERE extname='vector'`)

**Gotchas:**
- `tectonic` needs network access on first run to download LaTeX packages — ensure Docker build has internet
- Use `pgvector/pgvector:pg16` not the base postgres image

### Retrospective

**What changed from the plan:**
- Dockerfile CMD uses `uvicorn` directly instead of `poetry run uvicorn` since `virtualenvs.create false` installs packages to system Python — simpler and faster startup.
- Added `libgraphite2-3`, `libicu76`, `libssl3t64` as runtime dependencies for tectonic. The drop-sh binary links against these shared libraries which are not present in `python:3.12-slim`.
- Created `backend/.dockerignore` (not originally in the plan) to keep Docker build context small.
- Created a minimal `backend/src/main.py` with just `GET /api/v1/health` + DB connectivity check. This was needed to verify the Docker setup. Phase 1.4 will expand this file.
- Makefile docker targets updated to use `-f ../docker-compose.yml` since the compose file lives at repo root but the Makefile is in `backend/`.
- `docker-compose.yml` sets `DATABASE_URL` with `postgres` hostname in `environment:` block (overrides `.env` file's `localhost` value via pydantic-settings precedence).
- Poetry version pinned to `1.8.5` in Dockerfile for reproducible builds.

**Gotchas discovered:**
- `python:3.12-slim` (now Debian Trixie-based) uses `libicu76` not `libicu72`, and `libssl3t64` not `libssl3`. Package names change with Debian versions.
- The tectonic drop-sh script downloads the binary to the current directory; must explicitly `install` it to `/usr/local/bin/`.
- `poetry.lock` is gitignored in `backend/.gitignore`. Dockerfile uses `COPY pyproject.toml poetry.lock* ./` (glob) to handle missing lock file gracefully.

**Adjustments for upcoming sub-phases:**
- Phase 1.4 should expand `backend/src/main.py` (already exists with health endpoint) rather than creating it from scratch. Add CORS middleware, auth router includes, etc.
- Container names are `resumate-backend` and `resumate-postgres` (for `docker exec` commands in subsequent phases).

---

### 1.3 — Database Schema & Migrations

**Dependencies:** 1.2
**Complexity:** Medium

**Files to create:**
```
backend/src/models/
├── base.py                 # Declarative base + common mixins (UUID PK, timestamps)
├── user.py                 # User, RefreshToken
├── career.py               # CareerHistoryEntry
├── job.py                  # JobDescription
├── session.py              # Session
├── resume.py               # TailoredResume, ResumeTemplate
├── feedback.py             # FeedbackLog, SessionDecision
├── cover_letter.py         # CoverLetter
backend/src/core/database.py    # Async engine, session factory, get_db dependency
backend/alembic.ini
backend/alembic/
├── env.py
├── script.py.mako
└── versions/
    └── 001_initial_schema.py   # Generated via alembic revision --autogenerate
```

**Key model patterns:**
```python
# base.py
class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(default=func.now(), onupdate=func.now())

class UUIDMixin:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

# career.py — vector column
from pgvector.sqlalchemy import Vector
class CareerHistoryEntry(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "career_history_entries"
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"))
    entry_type: Mapped[str]         # work_experience, project, education, etc.
    title: Mapped[str]
    organization: Mapped[str | None]
    start_date: Mapped[date | None]
    end_date: Mapped[date | None]
    bullet_points: Mapped[list] = mapped_column(JSONB)
    tags: Mapped[list] = mapped_column(JSONB)
    source: Mapped[str]             # parsed_resume, user_provided, user_confirmed
    raw_text: Mapped[str | None] = mapped_column(Text)
    embedding = mapped_column(Vector(1536), nullable=True)
```

**database.py:**
```python
engine = create_async_engine(settings.database_url)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with async_session_maker() as session:
        yield session
```

**Makefile additions:** `migrate`, `migrate-create`

**Acceptance criteria:**
- `make migrate` applies all migrations without errors
- All tables exist with correct columns and types
- Vector columns (1536-dim) are created on career_history_entries, job_descriptions, session_decisions
- Foreign keys and indexes are in place
- Tests: model instantiation, basic CRUD with async session

### Retrospective (1.3)

**What changed from the plan:**
- `MetaData(naming_convention=...)` was added to `Base` for deterministic constraint names (not in original plan patterns but best practice).
- Append-only tables (`RefreshToken`, `ResumeTemplate`, `FeedbackLog`, `SessionDecision`) only have `created_at`, not `TimestampMixin` (which adds `updated_at`). They use `UUIDMixin` + `Base` directly.
- Migration file named `6323d988a33a_initial_schema.py` (Alembic auto-generated hash, not `001_initial_schema.py`).
- `script.py.mako` needed `import pgvector.sqlalchemy.vector` added so future autogenerated migrations include the pgvector import.

**Gotchas discovered:**
- **pytest-asyncio + asyncpg event loop mismatch**: asyncpg connections are bound to the event loop they were created on. pytest-asyncio runs fixture teardown on a different loop. Solution: use `NullPool` (no persistent connections), create engine inside the fixture, and skip async cleanup after `yield` in the fixture.
- **pydantic-settings strict mode**: `.env` must not contain extra keys not defined in `Settings`. Had to remove `OPENAI_API_KEY` and `ANTHROPIC_API_KEY` from `.env` (they'll be added when the Settings class is extended).
- **`from __future__ import annotations` + `TYPE_CHECKING`**: Required for forward references in relationship type hints across model files. Ruff's UP037 rule removes redundant string quotes when `__future__.annotations` is active, so `TYPE_CHECKING` imports are needed to resolve the names for mypy.

**Adjustments for upcoming sub-phases:**
- Phase 1.4 `conftest.py` already has a working `db_session` fixture with `NullPool` — extend it rather than rewrite.
- When adding new env vars to `.env.example`, ensure the `Settings` class in `config.py` includes them (or uses `Optional` with defaults) to avoid pydantic validation errors.

---

### 1.4 — FastAPI Skeleton + Auth

**Dependencies:** 1.3
**Complexity:** Medium

**Files to create:**
```
backend/src/main.py                     # FastAPI app, CORS, router includes
backend/src/api/auth.py                 # register, login, refresh
backend/src/schemas/auth.py             # RegisterRequest, LoginRequest, TokenResponse
backend/src/schemas/user.py             # UserResponse
backend/src/services/auth.py            # password hashing, JWT create/verify
backend/src/core/dependencies.py        # get_current_user dependency
backend/src/api/health.py              # GET /health
backend/tests/unit/test_auth.py
backend/tests/conftest.py              # Test DB setup, async fixtures
```

**Auth implementation:**
- `POST /api/v1/auth/register` — create user, return tokens
- `POST /api/v1/auth/login` — verify password, return access+refresh tokens
- `POST /api/v1/auth/refresh` — exchange refresh token for new access token
- JWT: access token (30min), refresh token (7 days, stored hashed in DB)
- `get_current_user` dependency: extract + verify JWT from `Authorization: Bearer <token>`

**`src/main.py`:**
```python
app = FastAPI(title="ResuMate API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, ...)
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(health_router, prefix="/api/v1", tags=["health"])
```

**Acceptance criteria:**
- `POST /api/v1/auth/register` creates user, returns JWT
- `POST /api/v1/auth/login` returns JWT for valid credentials, 401 for invalid
- `POST /api/v1/auth/refresh` returns new access token
- Protected endpoint returns 401 without token, 200 with valid token
- All tests pass

**Gotchas:**
- Use `bcrypt` via `passlib` for password hashing
- Store refresh tokens hashed (not plaintext) in the DB
- Test conftest needs an isolated test database (use `testcontainers` or a test DB URL)

### Retrospective (1.4)

**What changed from the plan:**
- Used `bcrypt` directly instead of `passlib[bcrypt]`. passlib is unmaintained and incompatible with bcrypt 4.1+ (missing `__about__` module, 72-byte password limit enforcement). `bcrypt.hashpw()` and `bcrypt.checkpw()` replace `passlib.CryptContext`.
- Added `GET /api/v1/auth/me` endpoint (not in original plan) as the protected endpoint to verify auth works. Returns the current user's info.
- Added `email-validator ^2.1` to dependencies — required by Pydantic's `EmailStr` type.
- Added ruff per-file ignore for B008 (`Depends()` in defaults) on `src/api/*.py` and `src/core/dependencies.py` — standard FastAPI pattern.
- Refresh tokens implement rotation: using a refresh token deletes it and issues a new one. Reusing an old token returns 401.
- Test conftest creates a module-level `_test_engine` with `NullPool` and overrides `get_db` globally on the app. Tests use `registered_user` fixture (registers via API) instead of inserting directly into DB, avoiding async session sharing issues with httpx ASGI transport.

**Gotchas discovered:**
- **passlib + bcrypt 5.0 incompatibility**: bcrypt 4.1+ removed `bcrypt.__about__` which passlib relies on for version detection. Also bcrypt 4.2+ enforces the 72-byte password limit strictly, causing `ValueError` on passlib's internal wrap-bug detection (which uses a 200+ byte test string). Solution: use bcrypt directly.
- **httpx ASGITransport + SQLAlchemy session sharing**: The ASGI transport creates requests in the same event loop but different async contexts. Overriding `get_db` to return the same session object from the fixture causes "invalid transaction state" errors after commits. Solution: override `get_db` with a factory that creates fresh sessions from the test engine, and use API-based fixtures (`registered_user`) instead of direct DB insertion.
- **`HTTPBearer` returns 403 (not 401) when no credentials are provided** — this is Starlette's default behavior when the `Authorization` header is missing entirely.

**Adjustments for upcoming sub-phases:**
- Phase 1.5 (frontend) can use the auth API as-is. The `/api/v1/auth/me` endpoint is useful for verifying token validity on page load.
- The `passlib` dependency can be removed from `pyproject.toml` in a future cleanup — it's no longer imported anywhere. Left in place to avoid unnecessary churn.

---

### 1.5 — Next.js Frontend Scaffolding

**Dependencies:** 1.4 (needs auth API to connect to)
**Complexity:** Medium

**Files to create:**
```
frontend/
├── package.json
├── tsconfig.json
├── tailwind.config.ts
├── next.config.ts
├── .eslintrc.json
├── components.json                     # shadcn/ui config
├── Dockerfile                          # For Docker Compose
├── src/
│   ├── app/
│   │   ├── layout.tsx                  # Root layout with providers
│   │   ├── page.tsx                    # Landing/redirect
│   │   ├── (auth)/
│   │   │   ├── login/page.tsx
│   │   │   └── register/page.tsx
│   │   └── (dashboard)/
│   │       ├── layout.tsx              # Sidebar + main content layout
│   │       └── page.tsx                # Dashboard home (empty initially)
│   ├── components/
│   │   ├── ui/                         # shadcn/ui components (Button, Input, Card, etc.)
│   │   ├── layout/
│   │   │   ├── Sidebar.tsx
│   │   │   └── Header.tsx
│   │   └── auth/
│   │       └── LoginForm.tsx
│   ├── context/
│   │   └── AuthProvider.tsx            # JWT state management, login/logout/refresh
│   ├── lib/
│   │   ├── api.ts                      # Fetch wrapper with auth headers + token refresh
│   │   └── utils.ts                    # CN helper for tailwind merge
│   └── types/
│       └── auth.ts                     # User, LoginRequest, TokenResponse types
```

**Key implementation:**

`AuthProvider.tsx`:
```typescript
// Stores JWT in localStorage, provides login/logout/user context
// Auto-refreshes token before expiry
// Redirects to /login if not authenticated on dashboard routes
interface AuthContext {
    user: User | null;
    login: (email: string, password: string) => Promise<void>;
    register: (name: string, email: string, password: string) => Promise<void>;
    logout: () => void;
    isLoading: boolean;
}
```

`lib/api.ts`:
```typescript
// Wraps fetch() with:
// - Base URL (process.env.NEXT_PUBLIC_API_URL)
// - Authorization header injection
// - Automatic 401 handling (attempt refresh, redirect to login)
// - JSON serialization/deserialization
export async function apiClient<T>(path: string, options?: RequestInit): Promise<T>
```

**shadcn/ui components to install:** Button, Input, Label, Card, Separator, Toast, Avatar, Dropdown Menu, Sheet (for mobile sidebar)

**Acceptance criteria:**
- `npm run dev` starts frontend on port 3000
- Register page creates user via API
- Login page authenticates, stores JWT, redirects to dashboard
- Dashboard shows empty layout with sidebar
- Refreshing page maintains auth state
- Navigating to /dashboard without auth redirects to /login

**Gotchas:**
- Next.js App Router: use client components (`"use client"`) for anything with state/effects
- shadcn/ui requires initial setup with `npx shadcn-ui@latest init`
- CORS: backend must allow `http://localhost:3000`

---

### 1.6 — WebSocket Streaming Infrastructure

**Dependencies:** 1.4 (backend), 1.5 (frontend)
**Complexity:** Medium

**Files to create:**
```
backend/src/api/websocket.py            # WS /api/v1/sessions/{id}/stream
backend/src/services/stream_manager.py  # Manages WebSocket connections and event dispatch
backend/src/schemas/ws_events.py        # Event type definitions matching protocol
backend/tests/unit/test_websocket.py
frontend/src/hooks/useWebSocket.ts      # Generic WebSocket hook
frontend/src/types/ws_events.ts         # TypeScript event types
```

**WebSocket event protocol (from PLAN_v2.md §11.2):**
```python
class WSEvent(BaseModel):
    type: Literal[
        "agent_start", "agent_end", "thinking",
        "stream_start", "stream_token", "stream_end",
        "progress", "approval_gate", "error"
    ]
    agent: str | None = None
    message: str | None = None
    section: str | None = None
    token: str | None = None
    current: int | None = None
    total: int | None = None
    label: str | None = None
    gate: str | None = None
    data: dict | None = None
    recoverable: bool | None = None
```

**Backend `stream_manager.py`:**
```python
class StreamManager:
    """Manages active WebSocket connections per session."""
    _connections: dict[str, list[WebSocket]]  # session_id -> websockets

    async def connect(self, session_id: str, ws: WebSocket) -> None
    async def disconnect(self, session_id: str, ws: WebSocket) -> None
    async def emit(self, session_id: str, event: WSEvent) -> None
```

**Frontend `useWebSocket.ts`:**
```typescript
function useWebSocket(sessionId: string, token: string) {
    const [events, setEvents] = useState<WSEvent[]>([]);
    const [isConnected, setIsConnected] = useState(false);
    const [currentAgent, setCurrentAgent] = useState<string | null>(null);
    const [streamingText, setStreamingText] = useState("");
    const [progress, setProgress] = useState<Progress | null>(null);
    // Connect, handle events, provide clean disconnect
}
```

**Acceptance criteria:**
- WebSocket connects with JWT authentication (token as query param)
- Backend can emit events to all connected clients for a session
- Frontend hook receives and categorizes events correctly
- Test: emit `stream_token` events → frontend assembles the text
- Test: emit `progress` events → frontend shows current/total
- Connection handles reconnection on disconnect

**Gotchas:**
- WebSocket auth: can't use `Authorization` header with browser WebSocket API — pass token as query param `?token=xxx`
- LangGraph streaming callbacks will be wired in Phase 4; this phase sets up the transport layer only

---

## Phase 2: Career History

### 2.1 — Resume Upload & Text Extraction

**Dependencies:** 1.4
**Complexity:** Small-Medium

**Files to create:**
```
backend/src/api/career.py               # POST /api/v1/career/import
backend/src/services/resume_extractor.py # PDF & DOCX text extraction
backend/src/schemas/career.py           # ImportRequest, ImportResponse, CareerEntrySchema
backend/tests/unit/test_resume_extractor.py
backend/tests/fixtures/                 # Sample PDF and DOCX resumes
```

**Implementation:**
```python
class ResumeExtractor:
    def extract_from_pdf(self, file_bytes: bytes) -> str:
        doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        return "\n".join(page.get_text() for page in doc)

    def extract_from_docx(self, file_bytes: bytes) -> str:
        doc = Document(BytesIO(file_bytes))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
```

**API endpoint:**
```python
@router.post("/import")
async def import_resume(
    file: UploadFile,
    current_user: User = Depends(get_current_user),
) -> ImportResponse:
    # Validate file type (pdf/docx/txt)
    # Extract text
    # Return raw text (parsing happens in 2.2b)
```

**Acceptance criteria:**
- Upload PDF → get extracted text
- Upload DOCX → get extracted text
- Rejects non-supported file types with 400
- Text preserves paragraph structure and bullet points

**Gotchas:**
- Two-column PDFs: `pymupdf` may interleave columns. Use `sort=True` in `get_text()` for basic column detection
- Very large files: set upload size limit (e.g., 10MB)

---

### 2.2a — LLM Config Infrastructure

**Dependencies:** 1.1
**Complexity:** Medium

**Files to create:**
```
backend/src/services/llm_config.py      # YAML config loader + model factory
backend/config/llm.yaml                 # Default config (with env var placeholders)
backend/tests/unit/test_llm_config.py
```

**Implementation:**
```python
class LLMConfig:
    """Loads config/llm.yaml, resolves env vars, provides model instances."""

    def __init__(self, config_path: str):
        self._config = self._load_yaml(config_path)

    def _load_yaml(self, path: str) -> dict:
        """Load YAML and resolve ${ENV_VAR} placeholders."""

    def get_chat_model(self, agent_name: str) -> BaseChatModel:
        """Return the configured chat model for a given agent."""
        model_key = self._config["agent_models"][agent_name]
        model_def = self._config["models"][model_key]
        provider = model_def["provider"]
        if provider == "openai":
            return ChatOpenAI(model=model_def["model"], ...)
        elif provider == "anthropic":
            return ChatAnthropic(model=model_def["model"], ...)
        # etc.

    def get_embedding_model(self) -> Embeddings:
        """Return the configured embedding model."""
```

**config/llm.yaml (from PLAN_v2.md §8.1):**
```yaml
providers:
  openai:
    api_key: ${OPENAI_API_KEY}
  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
models:
  gpt4o:
    provider: openai
    model: gpt-4o
  gpt4o-mini:
    provider: openai
    model: gpt-4o-mini
  embedding:
    provider: openai
    model: text-embedding-3-small
agent_models:
  job_analyst: gpt4o-mini
  resume_writer: gpt4o
  reviewer: gpt4o
  fact_checker: gpt4o-mini
  chat_agent: gpt4o
  ats_scoring: gpt4o-mini
  resume_parser: gpt4o
  cover_letter: gpt4o
```

**Acceptance criteria:**
- `LLMConfig("config/llm.yaml")` loads and resolves env vars
- `get_chat_model("resume_writer")` returns correct model type
- `get_embedding_model()` returns embedding model
- Missing env var raises clear error
- Tests mock env vars and verify correct model instantiation

---

### 2.2b — LLM-Based Resume Parsing

**Dependencies:** 2.1, 2.2a
**Complexity:** Medium

**Files to create:**
```
backend/src/services/resume_parser.py   # LLM-based structuring
backend/src/schemas/career.py           # ParsedResumeEntry (extends what 2.1 started)
backend/tests/unit/test_resume_parser.py
```

**Implementation:**
```python
class ResumeParser:
    def __init__(self, llm_config: LLMConfig):
        self.model = llm_config.get_chat_model("resume_parser")
        self.embedding_model = llm_config.get_embedding_model()

    async def parse(self, raw_text: str) -> list[ParsedResumeEntry]:
        """Send raw text to LLM with structured output schema."""
        # Uses .with_structured_output(ParsedResumeSchema)
        # Returns list of career entries with auto-extracted tags

    async def generate_embeddings(self, entries: list[ParsedResumeEntry]) -> None:
        """Generate and attach embeddings for each entry."""
```

**LLM prompt strategy:** Send the raw text with a system prompt instructing the LLM to:
1. Identify sections (work experience, education, skills, projects, etc.)
2. Group bullet points under correct entries
3. Extract dates, organizations, titles
4. Auto-tag technologies, skills, domains
5. Output as JSON matching `ParsedResumeEntry` schema

Use `model.with_structured_output()` for reliable JSON output.

**Acceptance criteria:**
- Raw resume text → list of structured CareerHistoryEntry objects
- Each entry has: title, organization, dates, bullets, tags, raw_text
- Entries are stored in DB with embeddings
- Tests with mocked LLM responses verify correct parsing

---

### 2.3 — Career History UI (Frontend)

**Dependencies:** 2.4, 1.5
**Complexity:** Medium

**Files to create:**
```
frontend/src/app/(dashboard)/career/page.tsx           # Career history page
frontend/src/components/career/
├── EntryCard.tsx              # Single career entry display
├── EntryForm.tsx              # Add/edit entry form
├── EntryList.tsx              # List of all entries
├── BulletPointEditor.tsx      # Inline bullet editing
├── TagBadge.tsx               # Technology/skill tag display
├── ImportDialog.tsx           # Upload resume dialog
└── ConfirmAllButton.tsx       # Mark all as user_confirmed
frontend/src/lib/api/career.ts # API client functions
frontend/src/types/career.ts   # TypeScript types
```

**Key features:**
- List all parsed entries as cards (title, org, dates, bullets, tags)
- Click to edit any field inline
- Add new entry via form dialog
- Delete entry with confirmation
- Upload new resume → show parsing progress → display parsed entries for review
- "Confirm All" button marks entries as `source=user_confirmed`
- Tags displayed as colored badges

**Acceptance criteria:**
- User can view all career history entries
- User can edit title, org, dates, bullets inline
- User can add a new entry manually
- User can delete an entry
- User can upload a resume and see parsed results
- "Confirm All" marks entries as verified
- All changes persist via API

---

### 2.4 — Career History API Endpoints

**Dependencies:** 1.3, 1.4
**Complexity:** Small

**Files to create/modify:**
```
backend/src/api/career.py              # Add CRUD endpoints (file started in 2.1)
backend/src/services/career.py         # Career history service layer
backend/tests/unit/test_career_api.py
```

**Endpoints:**
- `GET /api/v1/career/entries` — list all entries for current user
- `POST /api/v1/career/entries` — create entry manually
- `PUT /api/v1/career/entries/{id}` — update entry (regenerate embedding)
- `DELETE /api/v1/career/entries/{id}` — delete entry

All endpoints filter by `user_id` for data isolation. Entry updates trigger embedding regeneration.

**Acceptance criteria:**
- Full CRUD works, all endpoints return correct responses
- Only returns entries for the authenticated user
- Updating an entry regenerates its embedding
- Tests pass for all endpoints including auth checks

---

## Phase 3: Job Analysis & Matching

### 3.1 — Job Analyst Agent

**Dependencies:** 2.2a
**Complexity:** Medium

**Files to create:**
```
backend/src/agents/job_analyst/
├── __init__.py
├── agent.py                # LangGraph agent definition
├── prompts.py              # System prompt for JD analysis
├── schemas.py              # JDAnalysis Pydantic model
└── tools.py                # Web scraper tool (stub for now, full in 8.1)
backend/src/api/jobs.py     # POST /api/v1/jobs/parse, GET /api/v1/jobs/history
backend/src/schemas/job.py
backend/tests/unit/test_job_analyst.py
```

**`JDAnalysis` schema:**
```python
class JDAnalysis(BaseModel):
    role_title: str
    company_name: str | None
    seniority_level: str
    industry: str
    required_skills: list[str]
    preferred_skills: list[str]
    ats_keywords: list[str]
    tech_stack: list[str]
    responsibilities: list[str]
    qualifications: list[str]
    domain_expectations: list[str]  # e.g., "HIPAA for healthcare"
```

**Agent implementation:** Simple LangGraph graph — single node with structured output. Not a complex multi-step agent; JD parsing is well-defined.

**Acceptance criteria:**
- Paste JD text → get structured `JDAnalysis` with all fields populated
- Analysis is stored in `job_descriptions` table with embedding
- Tests with sample JDs verify field extraction

---

### 3.2 — Entry Retrieval & Match Scoring

**Dependencies:** 1.3, 3.1, 2.2b
**Complexity:** Medium

**Files to create:**
```
backend/src/services/retrieval.py       # Vector search + scoring
backend/src/services/match_scoring.py   # Match score calculation
backend/src/schemas/matching.py         # MatchResult, GapAnalysis
backend/tests/unit/test_retrieval.py
```

**Implementation:**
```python
class RetrievalService:
    async def find_relevant_entries(
        self, user_id: UUID, jd_embedding: list[float],
        entry_types: list[str] | None = None,
        tags: list[str] | None = None,
        top_k: int = 10,
    ) -> list[RankedEntry]:
        # pgvector cosine distance query
        # Optional tag-based filtering
        # Recency boost (configurable weight)

class MatchScorer:
    def score(
        self, jd_analysis: JDAnalysis, entries: list[CareerHistoryEntry]
    ) -> MatchResult:
        # Category breakdown: required_skills match, preferred match, experience level
        # Gap identification: JD requirements not covered by any entry
        # Recommended section ordering
```

**Acceptance criteria:**
- Given JD embedding, returns ranked career entries by relevance
- Match score includes category breakdown
- Gap analysis identifies unmatched JD requirements
- Section order recommendation based on JD emphasis

---

### 3.3 — Gate 1 UI (JD Analysis + Match Overview)

**Dependencies:** 1.5, 1.6, 3.1, 3.2
**Complexity:** Medium

**Files to create:**
```
frontend/src/app/(dashboard)/session/
├── new/page.tsx                       # Start new session (paste JD)
└── [id]/
    ├── page.tsx                       # Session view (routes to current gate)
    └── analysis/page.tsx              # Gate 1 view
frontend/src/components/session/
├── JDInput.tsx                        # Text area for JD input
├── AnalysisView.tsx                   # Display parsed requirements
├── MatchOverview.tsx                  # Score, selected entries, gaps
├── EntryToggle.tsx                    # Include/exclude entries
├── ContextInput.tsx                   # Add missing context
└── GateApprovalBar.tsx                # "Approve & Continue" bottom bar
frontend/src/lib/api/session.ts
frontend/src/types/session.ts
```

**Flow:**
1. User navigates to "New Session", pastes JD text
2. Frontend calls `POST /api/v1/sessions/start` → backend runs Job Analyst
3. Loading state with WebSocket progress events
4. Display: parsed requirements, match score, selected entries, gaps
5. User toggles entries on/off, adds context
6. "Approve & Continue" calls `POST /api/v1/sessions/{id}/approve` with gate="analysis"

**Acceptance criteria:**
- User pastes JD → sees analysis results
- Match score and gaps are visible
- User can toggle entries on/off
- User can add context text
- "Approve" advances to Gate 2 (calibration)

---

## Phase 4: Resume Writer Agent (Core)

### 4.1 — Resume Writer Agent (Basic)

**Dependencies:** 3.2, 2.2a
**Complexity:** Large

**Files to create:**
```
backend/src/agents/resume_writer/
├── __init__.py
├── agent.py                # LangGraph agent with career search tools
├── prompts.py              # System prompt (longest, most critical)
├── tools.py                # career_history_search, session_context
└── schemas.py              # EnhancedResume, EnhancedBullet, ResumeSection
backend/src/services/resume_session.py  # Session state management
backend/src/schemas/resume.py
backend/tests/unit/test_resume_writer.py
```

**`EnhancedResume` schema:**
```python
class EnhancedBullet(BaseModel):
    id: str                         # Deterministic: "{section_idx}_{bullet_idx}"
    original_text: str
    enhanced_text: str
    source_entry_id: UUID
    relevance_score: float

class ResumeSection(BaseModel):
    id: str
    section_type: str               # summary, experience, education, skills, etc.
    title: str
    entries: list[ResumeSectionEntry]

class EnhancedResume(BaseModel):
    summary: str
    sections: list[ResumeSection]
    skills: list[str]
    metadata: dict                  # section_order, total_bullets, etc.
```

**Resume Writer prompt strategy:**
- System prompt includes: JD analysis, selected entries, scoring context, gap awareness
- Instructions: select relevant entries, reorder sections, rephrase bullets, tailor summary
- Uses industry-appropriate terminology from Job Analyst's domain detection

**Acceptance criteria:**
- Given JD analysis + entries → produces complete `EnhancedResume` JSON
- Summary is tailored to the JD
- Bullets are rephrased to highlight JD relevance
- Skills section is tailored
- Tests with mocked LLM verify correct output structure

---

### 4.2 — Calibration Round (Gate 2)

**Dependencies:** 4.1, 1.6
**Complexity:** Medium

**Files to create/modify:**
```
backend/src/agents/resume_writer/agent.py    # Add calibration mode
backend/src/api/sessions.py                  # Gate 2 approval endpoint
frontend/src/app/(dashboard)/session/[id]/calibration/page.tsx
frontend/src/components/session/
├── CalibrationView.tsx            # Show first 2-3 bullets with diff
├── StyleFeedback.tsx              # Style/tone feedback input
└── BulletDiff.tsx                 # Simple word-level diff for calibration
```

**Flow:**
1. After Gate 1 approval, Resume Writer produces summary + first 2-3 bullets only
2. Frontend displays these with diff against originals
3. User provides style/tone feedback, edits bullets
4. Feedback is sent back; Resume Writer applies learned style to remaining bullets
5. "Approve" advances; writer completes the full resume

**Acceptance criteria:**
- Only 2-3 bullets are generated initially (not the full resume)
- User can edit bullets and provide style feedback
- After approval, full resume is generated matching the calibrated style
- Streaming shows progress as bullets are generated

---

### 4.3a — Gate 3 UI: Full Draft Display + Diff

**Dependencies:** 4.2, 1.5
**Complexity:** Medium

**Files to create:**
```
frontend/src/app/(dashboard)/session/[id]/review/page.tsx
frontend/src/components/session/
├── FullDraftView.tsx              # Complete resume display
├── BulletCard.tsx                 # Single bullet with diff + controls
├── SectionView.tsx                # Section grouping
├── SkillsEditor.tsx               # Add/remove skills
├── AnnotationBadge.tsx            # Reviewer/fact-check annotations
└── ATSScoreCard.tsx               # ATS score display
frontend/src/components/diff/
├── WordDiff.tsx                   # Word-level diff rendering
└── DiffProvider.tsx               # Diff computation (uses `diff` npm package)
```

**Key UX:** Complete enhanced resume with word-level diffs for every bullet (green additions, red removals). Each bullet has approve/reject/edit controls. Skills section with add/remove. ATS score displayed.

**Acceptance criteria:**
- Full enhanced resume displays with all sections
- Word-level diff visible for each bullet
- Skills section shows with add/remove
- Layout handles long resumes with smooth scrolling

---

### 4.3b — Gate 3: Per-Bullet Approval + Feedback Loop

**Dependencies:** 4.3a, 4.1
**Complexity:** Medium

**Files to modify:**
```
frontend/src/components/session/BulletCard.tsx   # Add approve/reject/edit interactions
backend/src/api/sessions.py                      # Feedback submission endpoint
backend/src/agents/resume_writer/agent.py        # Revision mode: rewrite rejected bullets
```

**Flow:**
1. User clicks approve/reject/edit on individual bullets
2. Rejected bullets can include feedback text
3. "Submit Feedback" sends all decisions to backend
4. Resume Writer rewrites rejected bullets incorporating feedback
5. Updated resume displays; user can review again or approve all

**Acceptance criteria:**
- Per-bullet approve/reject/edit works
- Rejected bullets trigger rewrite with user feedback
- Revised bullets show updated diffs
- "Approve All" advances to Gate 4
- Feedback is logged in `feedback_log` table

---

### 4.4 — LaTeX PDF Generation

**Dependencies:** 4.1
**Complexity:** Medium

**Files to create:**
```
backend/templates/latex/
├── professional.tex.j2            # First ATS-friendly template
backend/src/services/pdf_generator.py
backend/src/services/latex_sanitizer.py  # Escape special chars
backend/src/api/resumes.py         # GET /resumes/{id}/pdf
backend/tests/unit/test_pdf_generator.py
frontend/src/app/(dashboard)/session/[id]/final/page.tsx  # Gate 4
frontend/src/components/session/
├── PDFPreview.tsx                 # Embedded PDF viewer
└── FinalApproval.tsx              # Template select + generate button
```

**Jinja2 + LaTeX integration — CRITICAL:**
```python
# Use custom Jinja2 delimiters to avoid conflicts with LaTeX {}
env = jinja2.Environment(
    block_start_string=r'\BLOCK{',
    block_end_string='}',
    variable_start_string=r'\VAR{',
    variable_end_string='}',
    comment_start_string=r'\#{',
    comment_end_string='}',
    loader=jinja2.FileSystemLoader("templates/latex"),
)
```

**LaTeX sanitizer:**
```python
LATEX_SPECIAL = {'&': r'\&', '%': r'\%', '$': r'\$', '#': r'\#',
                 '_': r'\_', '{': r'\{', '}': r'\}', '~': r'\textasciitilde{}',
                 '^': r'\textasciicircum{}'}

def sanitize_for_latex(text: str) -> str:
    # Must handle backslash FIRST to avoid double-escaping
    text = text.replace('\\', r'\textbackslash{}')
    for char, escape in LATEX_SPECIAL.items():
        text = text.replace(char, escape)
    return text
```

**PDF compilation:**
```python
async def generate_pdf(resume: EnhancedResume, template_name: str) -> bytes:
    template = env.get_template(f"{template_name}.tex.j2")
    latex_source = template.render(resume=resume)
    # Write to temp file, compile with tectonic
    result = subprocess.run(["tectonic", temp_file], capture_output=True)
    return Path(output_path).read_bytes()
```

**Acceptance criteria:**
- EnhancedResume JSON → LaTeX → PDF produces a readable, ATS-friendly document
- Special characters in user content are properly escaped
- PDF download endpoint works
- Gate 4 UI shows PDF preview and download button
- Edge cases: long names, many bullets, empty sections, Unicode characters

---

## Phase 5: Fact Checking & Chat

### 5.1 — Fact Checker Agent

**Dependencies:** 4.1, 2.2a
**Complexity:** Medium

**Files to create:**
```
backend/src/agents/fact_checker/
├── __init__.py
├── agent.py                # LangGraph agent with career search
├── prompts.py
├── tools.py                # career_history_search, session_context_search
└── schemas.py              # FactCheckReport, ClaimVerification
backend/tests/unit/test_fact_checker.py
```

**`ClaimVerification` schema:**
```python
class ClaimVerification(BaseModel):
    claim_text: str
    bullet_id: str              # References EnhancedBullet.id
    status: Literal["verified", "unverified", "modified"]
    source_entry_id: UUID | None
    source_text: str | None     # Original text that backs the claim
    notes: str | None
```

**Acceptance criteria:**
- Takes enhanced resume + career history → produces verification report
- Each claim maps to verified/unverified/modified
- Verified claims include source reference
- Flags display as annotations at Gate 3

---

### 5.2 — Chat Agent

**Dependencies:** 2.2a, 1.6
**Complexity:** Large

**Files to create:**
```
backend/src/agents/chat/
├── __init__.py
├── agent.py                # LangGraph ReAct agent with all tools
├── prompts.py              # System prompt with routing instructions
├── tools.py                # Aggregated tools + session management
└── schemas.py              # ChatMessage, ChatResponse
backend/src/api/chat.py     # POST /chat/message, WS /chat/{session_id}/stream
backend/src/schemas/chat.py
backend/tests/unit/test_chat_agent.py
```

**Tools available to Chat Agent:**
- `search_career_history` — vector search career entries
- `add_career_entry` — store new info user provides
- `get_session_status` — check current gate/state
- `trigger_gate_reentry` — re-enter a previous gate
- `get_jd_analysis` — retrieve current JD analysis
- `get_enhanced_resume` — retrieve current draft

**Agent pattern:** LangGraph ReAct loop (agent → tools → agent) with `max_iterations=5`.

**Acceptance criteria:**
- Chat responds to freeform questions
- Can search career history ("Do I have Kubernetes experience?")
- Can store new info ("I also led a team of 5")
- WebSocket streaming for real-time responses
- Works with or without an active session
- Tool calls are visible in the UI

---

### 5.3 — Chat UI (Frontend)

**Dependencies:** 5.2, 1.5, 1.6
**Complexity:** Medium

**Files to create:**
```
frontend/src/components/chat/
├── ChatPanel.tsx              # Collapsible sidebar/drawer
├── MessageList.tsx            # Scrollable message list
├── MessageBubble.tsx          # User/assistant message
├── ChatInput.tsx              # Input + send
├── StreamingMessage.tsx       # Tokens arriving in real-time
├── ThinkingIndicator.tsx      # "Searching career history..."
└── ToolCallDisplay.tsx        # Shows tool usage
frontend/src/hooks/useChat.ts  # Chat state + WebSocket
frontend/src/lib/api/chat.ts
frontend/src/types/chat.ts
```

**Acceptance criteria:**
- Chat panel opens/closes from any page
- Messages stream token-by-token
- "Thinking" indicator shows during processing
- Tool usage is displayed
- Auto-scroll to bottom (respects user scroll position)

---

## Phase 6: Review & Polish (Moderate Detail)

### 6.1 — Reviewer Agent
- Two-pass review (recruiter + hiring manager perspectives) as a single agent
- Output: `ReviewAnnotation` objects tied to bullet IDs
- Display as colored badges at Gate 3

### 6.2 — ATS Scoring
- Primarily deterministic keyword matching
- Light LLM call for suggestions
- `ATSScore` with overall score + keyword gaps + format issues

### 6.3 — Diff View Polish
- Upgrade word-level diff from 4.3a to polished component
- Side-by-side and unified toggle views
- "Changes only" vs "full document" toggle

### 6.4 — Cover Letter Generation
- Reuse Resume Writer model with cover letter system prompt
- Input: JD analysis + matched entries + enhanced summary
- Store in `cover_letters` table

### 6.5 — Strength-of-Change Control
- Three-option select: conservative / moderate / aggressive
- Stored in `sessions.style_preference`
- Modifies Resume Writer system prompt behavior

---

## Phase 7: Learning & History (Moderate Detail)

### 7.1 — Past Session Learning
- Store `SessionDecision` on session completion
- Retrieve similar past sessions by JD embedding cosine similarity
- Inject as few-shot context into Resume Writer prompt

### 7.2 — Version History
- List past resumes with metadata (date, company, role, scores)
- View any past version, fork as new session starting point

### 7.3 — Retrieval Quality Dashboard
- Aggregate metrics from `feedback_log`: override rate, usage rate, rejection rate

---

## Phase 8: Extended Features (Moderate Detail)

### 8.1 — URL-Based JD Parsing
- `httpx` + `BeautifulSoup` for static pages
- Sanitize scraped content before LLM (untrusted input)

### 8.2 — Company Research Enrichment
- Web search tool (`tavily` or `duckduckgo-search`)
- Feed into cover letter and Gate 1 display

### 8.3 — Multiple LaTeX Templates
- 3-5 templates, all accepting same `EnhancedResume` JSON
- Template selector with preview thumbnails at Gate 4

### 8.4 — Multi-JD Mode
- Multiple JDs → composite requirements profile → generalized resume

### 8.5 — DOCX Export
- `python-docx` conversion from `EnhancedResume` JSON

---

## Suggested Implementation Order

The numbered order is mostly correct. Key adjustments:
1. **2.2a (LLM Config) should come before 2.1** — it's foundational infrastructure
2. **1.6 (WebSocket) was moved from 4.5** — needed earlier for streaming
3. **2.4 (API) before 2.3 (UI)** — UI needs the API to function
4. **4.1-4.4 are the critical path** — the core value proposition

```
1.1 → 1.2 → 1.3 → 1.4 ──→ 2.2a → 2.1 → 2.2b → 2.4 → 3.1 → 3.2 → 4.1 → 4.2 → 4.3a → 4.3b → 4.4
                       ↘ 1.5 → 1.6 → 2.3 → 3.3 → (Gate 2/3/4 UI from 4.2, 4.3a, 4.3b, 4.4)
                                                ↙
                       5.1 → 5.2 → 5.3 → 6.x → 7.x → 8.x
```

## Verification Strategy

After each phase, verify:
- **Phase 1:** `make docker-up && make test` — services start, auth works, DB migrates
- **Phase 2:** Upload a real resume → see parsed entries → edit → confirm
- **Phase 3:** Paste a real JD → see analysis + match overview → approve
- **Phase 4:** Complete calibration → review full draft → generate PDF → download
- **Phase 5:** Chat at any point → get relevant answers → fact-check flags visible
- **Phase 6-8:** Feature-specific manual testing + unit tests
