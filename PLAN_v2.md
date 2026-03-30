# ResuMate — Project Plan (v2)

> **Repository**: https://github.com/zarreh/resumate.git
>
> **Audience**: Family & friends — not a commercial SaaS product. No monetization, no admin panel, no user tiers.
>
> **Build philosophy**: Small, incremental sub-phases. Each sub-phase is designed to be completable in a single Claude Code session (basic subscription). Ship working increments, not grand architectures.
>
> **Changes from v1**: Reduced from 9 agents to 5 core agents, replaced 10+ approval gates with a focused 5-gate flow (with dedicated bullet-level approval), React from day one, LaTeX for PDF (user has templates), config-file LLM management with per-agent model selection, simpler RAG with quality tracking, realistic resume parsing with LLM + user approval. See [Appendix A](#appendix-a-v1-review-notes) for the full critique of v1.

---

## 1. Problem Statement

When applying for jobs, candidates must tailor their resumes to highlight the most relevant skills, experiences, and achievements for each position. This is time-consuming and error-prone. Candidates with extensive experience face the additional challenge of selecting and presenting the most relevant subset of their work. This tool automates that process using a multi-agent GenAI approach while strictly preserving factual accuracy.

### Core Constraints

- **Never fabricate** information not present in the original resume or explicitly provided by the user during interaction
- **Never exaggerate** responsibilities or achievements beyond what actually happened
- **Never add** skills or experiences the applicant does not have
- All enhancements must be verifiable against user-provided source material (resume, conversation, or explicit user confirmation)

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Frontend (Next.js / React)            │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────────┐  │
│  │  Chat Panel  │  │ Resume View  │  │ Career History│  │
│  │  (primary)   │  │ (diff/edit)  │  │  (structured) │  │
│  └─────────────┘  └──────────────┘  └───────────────┘  │
└──────────────────────────┬──────────────────────────────┘
                           │ REST API + WebSocket (JWT Auth)
┌──────────────────────────┴──────────────────────────────┐
│                    Backend (FastAPI)                      │
│  ┌──────────────────────────────────────────────────┐   │
│  │         LangGraph Orchestrator                    │   │
│  │  ┌────────────┐ ┌────────────┐ ┌──────────────┐  │   │
│  │  │Job Analyst │ │Resume Writer│ │  Reviewer    │  │   │
│  │  ├────────────┤ ├────────────┤ ├──────────────┤  │   │
│  │  │Fact Checker│ │ Chat Agent │ │              │  │   │
│  │  └────────────┘ └────────────┘ └──────────────┘  │   │
│  └──────────────────────────────────────────────────┘   │
│  ┌───────────────┐  ┌────────────┐  ┌───────────────┐  │
│  │ Background    │  │ Web Scraper│  │ PDF Generator │  │
│  │ Tasks (native)│  │(httpx/BS4) │  │ (LaTeX/Jinja) │  │
│  └───────────────┘  └────────────┘  └───────────────┘  │
└──────────────────────────┬──────────────────────────────┘
                           │
┌──────────────────────────┴──────────────────────────────┐
│              PostgreSQL + pgvector                        │
│  ┌────────────┐ ┌────────────────┐ ┌─────────────────┐  │
│  │ User/Auth  │ │ Career History │ │ Vector Store    │  │
│  │ Tables     │ │ (structured)   │ │ (embeddings)    │  │
│  └────────────┘ └────────────────┘ └─────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Key Architecture Decisions

| Decision | v1 | v2 | Rationale |
|---|---|---|---|
| Agents | 9 specialized agents | 5 core agents (Job Analyst, Resume Writer, Reviewer, Fact Checker, Chat) | Reduced from 9 but kept enough for clear separation of concerns and future extensibility |
| Approval gates | 10+ sequential gates | 5 focused gates (analysis → calibration bullets → full draft with per-bullet approve → skills/structure → final) | Dedicated bullet-level approval without the section-by-section waterfall |
| Frontend | Streamlit → React (rewrite) | Next.js from day one | Streamlit can't handle diff views, inline editing, or streaming; user needs strong React scaffolding from the start |
| Task queue | Celery + Redis | FastAPI BackgroundTasks + LangGraph async | LangGraph handles async natively; Celery adds ops overhead for no benefit at this scale |
| PDF engine | LaTeX | LaTeX + Jinja2 | User has LaTeX templates and knows it produces professional output; proven for the use case |
| RAG | HyDE + cross-encoder + multi-query + self-query + context budget | Vector search + keyword filtering + quality tracking | Start simple but measure retrieval quality from day one; add complexity based on evidence |
| LLM management | Database-driven multi-model platform with per-user tiers | Config file with per-agent model assignment | No admin panel — just a YAML/env config that maps each agent to a specific model/provider |
| Target audience | Implied SaaS with user tiers | Family & friends | No monetization, no admin panel, no cost budgets, no user tiers |

---

## 3. Agent Design

The system uses LangGraph to orchestrate 5 specialized agents. The design balances simplicity (fewer agents than v1's 9) with clear separation of concerns and room for future expansion.

**Design principle**: An agent is justified when it needs **tool access**, **state management**, or **autonomous decision-making**. Components that are a single LLM call with fixed input → output are implemented as LangGraph nodes (functions), not agents. The ATS scoring step is the one exception — it's primarily rule-based code with a light LLM assist, implemented as a utility function called within the workflow.

### 3.1 Agent Roster

#### 1. Job Analyst Agent
- Parses job descriptions (text or URL) into structured data
- Extracts: required skills, preferred skills, seniority level, ATS keywords, tech stack, industry/domain
- Detects industry-specific expectations (e.g., HIPAA for healthcare, PCI-DSS for fintech)
- **Tools**: web scraper (URL → text), web search (company research)
- On URL input: fetches page, extracts JD, optionally researches company
- Outputs a structured `JDAnalysis` object (Pydantic model)
- Caches parsed JD analysis for reuse

#### 2. Resume Writer Agent
- The core agent. Takes the JD analysis + user's career history and produces an enhanced resume
- Selects relevant entries, reorders sections, rephrases bullets, tailors the summary
- Incorporates scoring/gap awareness directly in its prompt (which entries are most relevant, what's missing, recommended section order)
- **Tools**: career history search (vector + keyword), session context retrieval, past session retrieval
- Handles the calibration flow: writes first 2-3 bullets, gets user feedback, applies learned style to the rest
- Uses industry-appropriate terminology based on Job Analyst's domain detection
- Can reframe transferable experience for cross-industry applications

#### 3. Reviewer Agent
- Reviews the enhanced resume from **two perspectives** (recruiter and hiring manager) in a single agent with two review passes
- Recruiter perspective: scannability, fabrication risk, screening pass likelihood, impact clarity
- Hiring manager perspective: technical depth, relevance to the role, qualification signals, missing context
- **Tools**: career history search (to check claims against source material)
- Outputs structured feedback attached to specific sections/bullets
- This is a full agent (not just a prompt) because it needs to cross-reference the original career history against the enhanced content and may need to search for specific entries

#### 4. Fact Checker Agent
- Cross-references every claim in the enhanced resume against the original career history + any user-provided information from the session
- **Tools**: career history search, session context search
- Flags any statement that cannot be traced to verified source material
- Outputs a structured report: each claim → source reference or "unverified" flag
- This is an agent (not just a prompt) because it needs to actively search the career history to find or fail to find backing evidence for each claim

#### 5. Chat Agent
- Always-available conversational agent — the primary interface
- Routes to Job Analyst or Resume Writer when needed
- Captures new user-provided information and stores it in the session context
- Handles freeform questions, clarifications, ad-hoc edit requests
- Can trigger re-entry to any previous workflow step
- **Tools**: all tools available to other agents + session management

### 3.2 ATS Scoring (Utility Function, Not an Agent)

- Keyword match scoring against JD — primarily deterministic code
- Counts keyword matches, checks section header formatting, validates date formats
- Light LLM call for nuanced suggestions (e.g., "consider adding 'distributed systems' which appears in the JD and aligns with your Kafka experience")
- Runs as a function node in the LangGraph workflow, not a full agent

### 3.3 Orchestration Flow

```
User uploads resume + provides JD (text or link)
    │
    ▼
[Resume Parser] ──── extracts structured career history entries (LLM-assisted)
    │ (only on first upload or new resume; stored for reuse)
    │
    ▼
╔══════════════════════════════════════════════════════════════╗
║  PARSING APPROVAL: User reviews parsed career history        ║
║  - Verify entries, dates, bullet attribution are correct     ║
║  - Edit/split/merge entries as needed                        ║
║  - This becomes the source of truth for all future sessions  ║
╚══════════════════════════════════════════════════════════════╝
    │
    ▼
[Job Analyst Agent] ──── parses JD, extracts requirements, detects industry
    │                     optional: company research enrichment
    ▼
╔══════════════════════════════════════════════════════════════╗
║  GATE 1: JD Analysis + Match Overview                        ║
║  Show: parsed requirements, industry detected, match score,  ║
║  selected career entries, identified gaps, recommended order  ║
║  User: approve / adjust entry selection / add missing context ║
╚══════════════════════════════════════════════════════════════╝
    │
    ▼
[Resume Writer Agent] ──── writes summary + first 2-3 bullet points
    │
    ▼
╔══════════════════════════════════════════════════════════════╗
║  GATE 2: Calibration Round                                   ║
║  Show: enhanced summary + first 2-3 bullets with diff        ║
║  User: provides style/tone feedback, edits, approves         ║
║  System: learns preferences → applies to remaining bullets   ║
╚══════════════════════════════════════════════════════════════╝
    │
    ▼
[Resume Writer Agent] ──── completes all remaining bullet points + skills section
    │                       using learned style from calibration
    ▼
[Reviewer Agent] ──── recruiter perspective + hiring manager perspective
[Fact Checker Agent] ──── verifies all claims against career history
[ATS Scoring] ──── keyword + format check
    │  (these can run in parallel)
    ▼
╔══════════════════════════════════════════════════════════════╗
║  GATE 3: Full Draft Review (with per-bullet approval)        ║
║  Show: complete enhanced resume with:                        ║
║  - Word-level diff for every bullet (original → enhanced)    ║
║  - Per-bullet approve / reject / edit buttons                ║
║  - Reviewer feedback as annotations on specific sections     ║
║  - Fact-check flags on specific claims                       ║
║  - ATS score + keyword gap suggestions                       ║
║  - Skills section with add/remove controls                   ║
║  User: approve/reject/edit individual bullets and sections,  ║
║  request rewrites with feedback, adjust section order         ║
╚══════════════════════════════════════════════════════════════╝
    │
    ▼
[Resume Writer Agent] ──── rewrites rejected bullets with user feedback,
    │                       incorporates all edits, produces final draft
    ▼
╔══════════════════════════════════════════════════════════════╗
║  GATE 4: Final Approval                                      ║
║  Show: final resume preview (rendered), ATS score,           ║
║  template selection, output format choice                    ║
║  User: approve → generate PDF, or request more changes       ║
╚══════════════════════════════════════════════════════════════╝
    │
    ▼
[PDF Generator] ──── renders final LaTeX → PDF

--- At any point: Chat Agent is available for questions, edits, and new info ---
--- Chat can trigger re-entry to any previous gate ---
```

### 3.4 Gate Design Summary

| Gate | Purpose | User Actions |
|---|---|---|
| Parsing Approval | Verify LLM parsed the resume correctly | Edit entries, fix dates, reassign bullets |
| Gate 1: Analysis | Confirm JD understanding + entry selection | Adjust which entries are included, add context |
| Gate 2: Calibration | Set style/tone preferences from first bullets | Edit bullets, provide style feedback |
| Gate 3: Full Draft | Detailed per-bullet review of the complete resume | Approve/reject/edit each bullet, reorder sections |
| Gate 4: Final | Last check before PDF generation | Template selection, final approve |

**Key difference from v1**: v1 had gates for summary, first bullets, remaining bullets, skills, structure, reviewer feedback, fact-check, and final — all as separate sequential steps. v2 collapses the detailed review into Gate 3 where the user sees everything at once with per-bullet controls. The calibration round (Gate 2) is the only bullet-specific gate before the full draft.

### 3.5 Learning from Past Sessions

The system improves over time based on user interactions:

- After each completed session, store: JD embedding, industry, role title, which career entries were selected, the enhanced bullet texts, user feedback (approve/reject/edit decisions), style preferences observed
- On new sessions, retrieve the 2-3 most similar past sessions by JD embedding similarity + role title matching
- Use past decisions as **few-shot context** for the Resume Writer:
  - "For a similar JD, you selected these entries" → suggest same entries first
  - "The user preferred this bullet style" → use as style reference
  - "These bullets were rejected/edited" → avoid similar patterns
  - "This section order worked" → propose as default

**How this plays out over time:**
- **First session**: Big transformation from the raw resume to a professionally enhanced version. Heavy user involvement at every gate.
- **Second session (similar role)**: System proposes selections and style based on session 1. User approves faster, edits less.
- **Third+ session (same role type)**: System drafts near-complete resume. Gates 2-3 become quick approval passes. But the tool always defers to the user — auto-approval is opt-in, never forced.
- **Different role type**: System recognizes it's a new territory (different JD cluster), falls back to more conservative suggestions, asks for calibration again.

This is implemented via simple vector similarity retrieval of past sessions. No need for HyDE or cross-encoders — the sessions are the user's own data, and the vocabulary is consistent.

---

## 4. Career History (Structured Data Store)

### 4.1 Design Philosophy

The comprehensive resume is decomposed into structured, searchable entries via LLM-assisted parsing. Each entry represents a single work experience, project, education, etc. This structured format enables selecting/excluding entries per JD, reordering, per-bullet enhancement, and tracking what was used where.

### 4.2 Data Model

```
CareerHistoryEntry:
  id: UUID
  user_id: FK → User
  entry_type: ENUM [work_experience, project, education, certification,
                     publication, volunteer, award, other]
  title: str
  organization: str (nullable)
  start_date: date (nullable)
  end_date: date (nullable)
  bullet_points: list[str]
  tags: list[str]             # auto-extracted: technologies, skills, domains
  source: ENUM [parsed_resume, user_provided, user_confirmed]
  raw_text: text              # original text before parsing (for fact-checking)
  embedding: vector(1536)     # single embedding of the full entry
  created_at: timestamp
  updated_at: timestamp
```

### 4.3 Resume Parsing

Resume parsing is **deceptively hard**. Resumes have wildly inconsistent formatting — headers vary, date formats differ, sections are ordered differently, multi-column layouts break text extraction.

#### Parsing Strategy

1. **Text extraction**: Use `pymupdf` for PDF, `python-docx` for DOCX. Extract raw text preserving structure (line breaks, section boundaries).
2. **LLM-based structuring**: Send extracted text to an LLM with a structured output schema (Pydantic model). The LLM identifies sections, groups bullets under the right experience, extracts dates, and tags skills/technologies.
3. **User verification** (Parsing Approval gate): Present parsed entries back to the user. **This is critical** — the user must confirm correctness before it becomes the source of truth. Misattributed bullets or wrong dates will cascade errors through every enhancement session.
4. **Iterative correction**: User edits, splits/merges entries, reassigns bullets. The corrected version is stored with `source=user_confirmed`.
5. **Manual entry**: Users can also add/edit entries manually through the UI at any time, bypassing file upload entirely.

#### Supported Input Formats
- **PDF** (most common) — `pymupdf` handles most standard PDFs; two-column layouts require extra heuristics
- **DOCX** — `python-docx` for text extraction
- **Plain text** — direct paste, easiest to parse
- **Manual form input** — add/edit entries through the UI

---

## 5. Retrieval Strategy

### 5.1 Start Simple, Measure, Improve

The retrieval problem is **well-bounded**: a user has 5-30 career history entries, and we need to rank them against a JD. Start with simple retrieval, but **measure quality from day one** so we know when and where to invest in improvements.

**Initial approach:**
- **Vector similarity** (pgvector cosine distance) between JD embedding and entry embeddings
- **Tag-based filtering**: filter by `entry_type` and `tags` where useful (e.g., only work experience, filter by tech stack)
- **Recency boost**: weight recent entries higher (configurable)
- Return top-K entries, pass to the Resume Writer Agent

### 5.2 Retrieval Quality Tracking (Built-In from Day One)

Every retrieval interaction is tracked so we can measure and improve:

| Metric | What It Measures | How It's Tracked |
|---|---|---|
| **User override rate** | How often the user adds entries the system didn't retrieve or removes entries it did at Gate 1 | Log user adjustments at Gate 1 |
| **Entry usage rate** | What fraction of retrieved entries actually appear in the final resume | Compare retrieved set vs. final resume content |
| **Bullet rejection rate** | How often enhanced bullets are rejected at Gate 3 — could signal wrong entries were selected | Log per-bullet approve/reject at Gate 3 |
| **Re-retrieval triggers** | How often the user asks the Chat Agent to find different entries mid-session | Log Chat Agent tool calls to career history search |

These metrics are stored in `feedback_log` and can be reviewed to decide when retrieval needs improvement.

### 5.3 When to Add Complexity

Add advanced retrieval techniques **only when metrics justify them**:

| Technique | Add When | Signal |
|---|---|---|
| BM25 keyword search (hybrid) | Exact skill matches (e.g., "Kubernetes") are missed by vector search | User frequently adds entries with exact keyword matches at Gate 1 |
| Multi-query decomposition | JDs with many distinct requirements return biased results | User overrides skew toward one requirement type |
| HyDE | Vocabulary gap between JD and resume is measurable | High-quality entries exist but aren't retrieved because phrasing differs |
| Cross-encoder re-ranking | Too many irrelevant entries in top results | Low entry usage rate despite good entries existing |
| Per-bullet-point embeddings | Key matches buried in one bullet of a larger entry | User adds entries where the relevant part is a single bullet |

---

## 6. Job Description Handling

### 6.1 Single JD Mode (Phase 1)
- Accept a single JD as plain text pasted into the chat
- Produces a resume tailored to that specific job posting

### 6.2 URL-Based JD Input (Phase 2)
- Parse a URL to extract the job description
- **Start with**: `httpx` + BeautifulSoup for static pages (covers most job boards' server-rendered content)
- **Add Playwright** only when you hit JS-rendered pages that httpx can't handle (LinkedIn, Workday, some Greenhouse instances)
- Extract: title, company, location, requirements, responsibilities
- Playwright adds significant Docker image size and complexity — don't add it until you need it

### 6.3 Multi-JD / Job Title Mode (Phase 3)
- User provides multiple JDs targeting the same role category
- System produces a composite requirements profile and a single generalized resume
- Same logic as v1, but deferred to Phase 3 instead of being architected upfront

### 6.4 Company Research Enrichment (Phase 3)
- Web search for company values, tech stack, culture signals
- Feed to Resume Writer and Cover Letter generation
- Defer because: requires reliable web search tool integration, results are supplementary not core

---

## 7. Resume Output & Templating

### 7.1 PDF Generation: LaTeX + Jinja2

LaTeX is proven for producing professional, publication-quality resumes. The user has existing LaTeX templates that produce the desired output.

**Template system:**
- Content is stored as structured JSON (separate from presentation)
- Jinja2 templates generate LaTeX source from JSON content
- LaTeX compiles to PDF via `pdflatex` or `tectonic`
- **Separation of concerns**: the Resume Writer Agent outputs structured JSON, the template layer renders it — user can switch templates without re-tailoring
- User-provided LaTeX templates can be added alongside built-in ones
- 2-3 professional built-in templates, expandable
- All templates are ATS-optimized (single-column, standard section headers)

**Handling LaTeX pitfalls:**
- Sanitize all user-provided text before injecting into LaTeX (escape special characters: `&`, `%`, `$`, `#`, `_`, `{`, `}`, `~`, `^`, `\`)
- Use `tectonic` over `pdflatex` where possible — it auto-downloads packages and has better error messages
- Docker image uses `texlive-full` or a curated subset to ensure all packages are available
- Template validation: test each template with edge-case content (long names, special characters, many bullets) as part of CI

### 7.2 Output Formats
- **PDF** (primary) — LaTeX-compiled, ATS-friendly
- **Plain text** — for copy-paste into online application forms
- **DOCX** — via `python-docx` for recruiters who require it (later phase)
- **JSON** — structured data, always available (it's the internal format)

### 7.3 ATS Compliance
- No tables, columns, or complex formatting that breaks ATS parsers
- Standard section headers (Experience, Education, Skills)
- Machine-readable dates and contact info
- Keyword density aligned with JD

---

## 8. LLM Configuration

### 8.1 Config-File Driven, Per-Agent Model Assignment

Each agent and each utility step can be assigned a **different model and provider** via a single config file. No database, no admin panel — just edit the YAML and restart (or override with env vars).

```yaml
# config/llm.yaml
providers:
  openai:
    api_key: ${OPENAI_API_KEY}
  anthropic:
    api_key: ${ANTHROPIC_API_KEY}
  google:
    api_key: ${GOOGLE_API_KEY}
  ollama:
    base_url: http://localhost:11434

models:
  gpt4o:
    provider: openai
    model: gpt-4o
  gpt4o-mini:
    provider: openai
    model: gpt-4o-mini
  claude-sonnet:
    provider: anthropic
    model: claude-sonnet-4-20250514
  gemini-flash:
    provider: google
    model: gemini-2.0-flash
  local-llama:
    provider: ollama
    model: llama3.1:8b
  embedding:
    provider: openai
    model: text-embedding-3-small

# Each agent/step maps to a model key from above
agent_models:
  job_analyst: gpt4o-mini           # structured extraction — fast model is fine
  resume_writer: gpt4o              # core output quality — use best available
  reviewer: gpt4o                   # nuanced critique needs strong reasoning
  fact_checker: gpt4o-mini          # comparison/verification — structured task
  chat_agent: gpt4o                 # user-facing responses need quality
  ats_scoring: gpt4o-mini           # light LLM assist for keyword suggestions
  resume_parser: gpt4o              # parsing needs quality to get structure right
  cover_letter: gpt4o               # creative writing quality matters
```

**Design:**
- The LangChain model abstraction layer means all agents interact through a unified interface
- Swapping any agent's model requires changing one line in the config — zero code changes
- Any supported LangChain provider can be added (OpenAI, Anthropic, Google, Ollama, etc.)
- Users who want full data privacy can point all agents to a local Ollama model
- The `models` section defines the available model pool; `agent_models` maps agents to models

### 8.2 Cost Tracking (Lightweight)

- LangSmith automatically logs token usage per LLM call
- Calculate and display cost per session after completion
- No budgets, tiers, or automated cost controls — this is a family & friends tool

---

## 9. Features by Phase

Features are grouped roughly by phase. The detailed sub-phase breakdown is in Section 15.

### Core Features (Phase 1)
- Resume upload + LLM-based parsing with user approval
- Career history management (view, edit, add entries)
- JD input (text) + Job Analyst Agent (structured extraction)
- Resume Writer Agent (full enhancement with calibration)
- Fact Checker Agent
- 5-gate approval workflow (parsing → analysis → calibration → full draft → final)
- Chat Agent for freeform interaction
- PDF output (LaTeX, 1 template)
- WebSocket streaming + progress indicators

### Enhancement Features (Phase 2)
- Reviewer Agent (recruiter + hiring manager perspectives)
- ATS scoring
- Side-by-side diff view with per-bullet approve/reject
- Cover letter generation
- Strength-of-change control (conservative/moderate/aggressive)
- Past session learning (store + retrieve decisions)

### Extended Features (Phase 3)
- URL-based JD parsing (httpx + BS4, Playwright if needed)
- Company research enrichment
- Version history (browse, compare, fork)
- Multiple LaTeX templates (3-5)
- DOCX export
- Multi-JD / job title mode

### Future Features (Phase 4+)
- Interview Prep Mode
- LinkedIn Optimization
- Batch Apply Mode
- Networking Outreach Drafts
- Quantification Assistant
- Advanced RAG (if retrieval metrics justify it)

---

## 10. Tech Stack

### 10.1 Language & Tooling
- **Language**: Python 3.12+
- **Package Manager**: Poetry
- **Build Automation**: Makefile
- **Containerization**: Docker + Docker Compose
- **Documentation**: MkDocs with Material theme
- **Code Quality**: ruff (linting + formatting), mypy (type checking), pre-commit hooks
- **Testing**: pytest, pytest-asyncio, pytest-cov

### 10.2 Backend
- **Framework**: FastAPI
- **Agent Framework**: LangChain / LangGraph / LangSmith
- **Async Processing**: FastAPI BackgroundTasks + LangGraph async (no Celery)
- **WebSocket**: FastAPI native WebSocket for streaming
- **Web Scraping**: httpx + BeautifulSoup; add Playwright later if needed for JS-rendered pages
- **PDF Generation**: LaTeX (via `tectonic` or `pdflatex`) + Jinja2 templates
- **DOCX Generation**: python-docx (later phase)
- **Resume Parsing**: pymupdf (PDF), python-docx (DOCX), LLM-based structuring
- **Database ORM**: SQLAlchemy 2.0 + Alembic

### 10.3 Frontend
- **Framework**: Next.js (React) from day one
- **Language**: TypeScript
- **Styling**: Tailwind CSS (utility-first, fast to build with)
- **UI Components**: shadcn/ui (beautiful, accessible, copy-paste components built on Radix)
- **State Management**: React built-in (useState/useContext) + TanStack Query for server state
- **WebSocket**: native WebSocket API or `socket.io-client`
- **Key Phase 1 Components**: chat panel, resume preview, career history list, auth pages
- **Key Phase 2 Components**: diff view (use `diff` library), inline editing, template selector, strength slider

> **Note for implementation**: The project owner is not experienced with JavaScript/React. All frontend implementation should include:
> - Well-commented code explaining React patterns (components, hooks, state, effects)
> - Clear file/folder structure with a README explaining conventions
> - TypeScript for type safety (catches errors at compile time, similar to Python type hints)
> - shadcn/ui for UI components to avoid building common elements from scratch
> - Next.js App Router for routing (file-based, minimal boilerplate)
> - Implementation sessions should include explanation of *why* code is structured a certain way, not just *what* it does

### 10.4 Database
- **PostgreSQL + pgvector**
- Single database for structured data + vector embeddings

### 10.5 Observability
- **LangSmith**: tracing, evaluation, prompt iteration, cost tracking
- Application logs (structured JSON) for debugging

---

## 11. Real-Time UX

### 11.1 Streaming & Progress

The user must always know what the system is doing:

- **Token-level streaming**: all LLM output streams to the frontend via WebSocket (user sees text appear in real-time)
- **Agent activity indicator**: show which step is active (e.g., "Analyzing job description...", "Writing enhanced resume...")
- **Progress for multi-step operations**: "Parsing resume... Extracted 7 entries", "Enhancing bullet 3 of 12"
- **Interruptible**: user can cancel a generation mid-stream

### 11.2 WebSocket Event Protocol

```json
{"type": "agent_start",    "agent": "job_analyst",    "message": "Parsing job description..."}
{"type": "agent_end",      "agent": "job_analyst"}
{"type": "thinking",       "agent": "resume_writer",  "message": "Selecting relevant experience..."}
{"type": "stream_start",   "section": "summary"}
{"type": "stream_token",   "token": "Experienced "}
{"type": "stream_end",     "section": "summary"}
{"type": "progress",       "current": 3, "total": 12, "label": "Enhancing bullet points"}
{"type": "approval_gate",  "gate": "full_draft",      "data": {...}}
{"type": "error",          "message": "...",           "recoverable": true}
```

---

## 12. Security & Privacy

### 12.1 Authentication & Authorization
- JWT-based auth with refresh tokens
- Simple user accounts (no roles/tiers — family & friends tool)
- Rate limiting on all API endpoints (prevents accidental abuse)
- Input validation and sanitization on all endpoints (Pydantic models)

### 12.2 Data Protection
- TLS for all data in transit
- Encrypt sensitive fields at rest (PII columns in PostgreSQL)
- **PII and LLMs — realistic approach**: Resumes *are* PII. You cannot strip names, companies, and job titles and still have a usable resume to enhance. Accept that resume content is sent to LLM providers and mitigate:
  - Choose providers with strong data retention policies (e.g., OpenAI API data is not used for training by default)
  - Document clearly in the UI which data is sent to external APIs (transparency)
  - Support local models (Ollama) via the config file for users who want full data privacy — set all `agent_models` to a local model and no data leaves the machine
  - Never log full resume content to application logs, error trackers, or observability tools — log session IDs and metadata only
  - PII stays in the database; only the necessary context is sent to LLM calls (not the entire career history for every call)

### 12.3 Input Sanitization & Prompt Safety
- All user inputs validated and sanitized before entering LLM prompts
- **Scraped content (JDs, URLs) is untrusted** — sanitize before including in prompts:
  - Strip HTML tags, JavaScript, control characters
  - Detect known prompt injection patterns (system prompt overrides, instruction delimiters)
  - Truncate excessively long inputs
- Use structured tool-call interfaces (Pydantic models), not string interpolation, for agent ↔ tool communication
- Topic guardrails: agents refuse off-topic requests via system prompt instructions

### 12.4 Data Isolation
- Strict per-user data isolation — all database queries filter by `user_id`
- Agent system prompts include: "only reference information from the current user"
- No shared state between user sessions

### 12.5 Data Retention
- User can delete all their data (all career history, sessions, resumes, feedback)
- Data stays until explicitly deleted — no auto-purge (small user base, no compliance pressure)

---

## 13. Database Schema

```sql
-- Users & Auth
users (id UUID PK, email, hashed_password, name, created_at, updated_at)
refresh_tokens (id UUID PK, user_id FK, token_hash, expires_at, created_at)

-- Career History
career_history_entries (
    id UUID PK, user_id FK, entry_type VARCHAR,
    title VARCHAR, organization VARCHAR,
    start_date DATE, end_date DATE,
    bullet_points JSONB, tags JSONB,
    source VARCHAR, raw_text TEXT,
    embedding vector(1536),
    created_at TIMESTAMP, updated_at TIMESTAMP
)

-- Job Descriptions
job_descriptions (
    id UUID PK, user_id FK, raw_text TEXT, parsed_data JSONB,
    source_url VARCHAR, company_name VARCHAR,
    role_title VARCHAR, industry VARCHAR,
    embedding vector(1536), created_at TIMESTAMP
)

-- Sessions
sessions (
    id UUID PK, user_id FK, job_description_id FK,
    status VARCHAR,
    langgraph_thread_id VARCHAR,   -- for LangGraph checkpoint persistence
    style_preference VARCHAR,       -- conservative / moderate / aggressive
    created_at TIMESTAMP, updated_at TIMESTAMP
)

-- Outputs
tailored_resumes (
    id UUID PK, user_id FK, session_id FK, job_description_id FK,
    content_json JSONB, template_id UUID FK,
    version INT, ats_score FLOAT, match_score FLOAT,
    parent_version_id UUID FK NULLABLE,  -- for version forking
    created_at TIMESTAMP
)
cover_letters (
    id UUID PK, user_id FK, session_id FK,
    content TEXT, version INT, created_at TIMESTAMP
)

-- Feedback & Learning
feedback_log (
    id UUID PK, session_id FK,
    gate VARCHAR,                    -- which gate this feedback came from
    entry_type VARCHAR,              -- bullet, section, summary, skill, etc.
    original_text TEXT,
    enhanced_text TEXT,
    user_action VARCHAR,             -- approved, rejected, edited
    user_comment TEXT,
    created_at TIMESTAMP
)

-- Past Session Learning
session_decisions (
    id UUID PK, session_id FK,
    jd_embedding vector(1536),
    role_title VARCHAR, industry VARCHAR,
    selected_entry_ids JSONB,
    section_order JSONB,
    style_notes TEXT,
    created_at TIMESTAMP
)

-- Templates
resume_templates (
    id UUID PK, name VARCHAR, description TEXT,
    template_file VARCHAR, preview_image VARCHAR,
    is_active BOOLEAN, created_at TIMESTAMP
)
```

---

## 14. API Endpoints

```
# Auth
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh

# Career History
GET    /api/v1/career/entries
POST   /api/v1/career/entries
PUT    /api/v1/career/entries/{id}
DELETE /api/v1/career/entries/{id}
POST   /api/v1/career/import              # upload resume → parse into entries

# Job Descriptions
POST   /api/v1/jobs/parse                  # text (or URL) → structured JD
GET    /api/v1/jobs/history

# Enhancement Workflow
POST   /api/v1/sessions/start              # begin enhancement session
GET    /api/v1/sessions/{id}
POST   /api/v1/sessions/{id}/approve       # approve a gate
POST   /api/v1/sessions/{id}/feedback      # provide feedback at a gate
WS     /api/v1/sessions/{id}/stream        # WebSocket for real-time updates

# Chat
POST   /api/v1/chat/message
WS     /api/v1/chat/{session_id}/stream    # WebSocket for chat streaming

# Outputs
GET    /api/v1/resumes
GET    /api/v1/resumes/{id}
GET    /api/v1/resumes/{id}/pdf
GET    /api/v1/resumes/{id}/txt
GET    /api/v1/resumes/{id}/diff
GET    /api/v1/resumes/{id}/docx           # Phase 8

# Templates
GET    /api/v1/templates

# Cover Letter
POST   /api/v1/cover-letter/generate
GET    /api/v1/cover-letter/{id}

# Version History
GET    /api/v1/resumes/history              # all past versions with metadata
GET    /api/v1/resumes/{id}/versions        # versions for a specific resume
POST   /api/v1/resumes/{id}/fork            # fork as starting point for new session
```

---

## 15. Development Phases

> **Sizing principle**: Each sub-phase is designed to be completable in **a single Claude Code session** (basic subscription). This means each sub-phase is a focused, well-defined task with clear inputs, outputs, and acceptance criteria. No sub-phase depends on "figure out the architecture" — the architecture decisions are in this plan.

---

### Phase 1: Foundation & Infrastructure

#### 1.1 — Project Scaffolding
- Initialize Poetry project with `pyproject.toml` (Python 3.12+)
- Create project folder structure (group by domain):
  ```
  src/
    api/           # FastAPI routes
    agents/        # LangGraph agents
    models/        # SQLAlchemy + Pydantic models
    services/      # business logic
    core/          # config, auth, dependencies
  tests/
  docs/
  config/
  templates/       # LaTeX templates
  ```
- Create Makefile with targets: `install`, `dev`, `test`, `lint`, `format`, `typecheck`
- Set up ruff config, mypy config, pre-commit hooks
- Create `.env.example` with all required env vars
- Create `README.md` with setup instructions
- **Output**: Running `make install && make lint` works. Empty project passes all checks.

#### 1.2 — Docker Compose Setup
- Create `Dockerfile` for backend (Python + LaTeX via `tectonic`)
- Create `docker-compose.yml` with services: backend, postgres (with pgvector extension), redis (for future use but cheap to include)
- Postgres container uses `pgvector/pgvector:pg16` image
- Create `scripts/init-db.sh` for database initialization
- Create `make docker-build`, `make docker-up`, `make docker-down` targets
- **Output**: `make docker-up` starts all services. Backend can connect to Postgres.

#### 1.3 — Database Schema & Migrations
- Set up SQLAlchemy 2.0 with async engine
- Create Alembic configuration and initial migration
- Define all core models: `User`, `CareerHistoryEntry`, `JobDescription`, `Session`, `TailoredResume`, `FeedbackLog`, `SessionDecision`, `ResumeTemplate`
- Create pgvector extension and vector columns
- Add migration targets to Makefile: `make migrate`, `make migrate-create`
- **Output**: `make migrate` applies all migrations. Tables exist in Postgres with correct schema.

#### 1.4 — FastAPI Skeleton + Auth
- Create FastAPI app with CORS, error handling, health check endpoint
- Implement JWT auth: register, login, refresh token endpoints
- Create Pydantic request/response schemas for auth
- Create auth dependency (`get_current_user`) for protected routes
- Add `/api/v1/` prefix to all routes
- Write tests for auth endpoints (register, login, refresh, protected route)
- **Output**: Can register a user, login, get JWT, access a protected endpoint. Tests pass.

#### 1.5 — Next.js Frontend Scaffolding
- Initialize Next.js project (App Router, TypeScript, Tailwind CSS)
- Install and configure shadcn/ui
- Create basic layout: sidebar + main content area
- Create pages: login, register, dashboard (empty)
- Implement auth flow: login form → JWT storage → protected routes → redirect
- Set up API client (fetch wrapper with auth headers)
- Add frontend to Docker Compose (or use `make dev-frontend` for local dev)
- **Output**: Can register, login, see empty dashboard. Auth state persists across page reloads.

---

### Phase 2: Career History

#### 2.1 — Resume Upload & Text Extraction
- Create file upload endpoint (`POST /api/v1/career/import`)
- Implement PDF text extraction using `pymupdf`
- Implement DOCX text extraction using `python-docx`
- Return extracted raw text to frontend
- Store uploaded file metadata in database
- Write tests for parsing with sample PDF and DOCX files
- **Output**: Upload a resume PDF → get structured text back via API.

#### 2.2 — LLM-Based Resume Parsing
- Create resume parsing service that sends extracted text to LLM
- Define Pydantic schema for parsed output (list of `CareerHistoryEntry` objects)
- Use LLM structured output (JSON mode) to get reliable parsing
- Auto-extract tags (technologies, skills, domains) per entry
- Generate embedding for each parsed entry
- Store parsed entries in `career_history_entries` table
- Wire up the LLM model from `config/llm.yaml` (`resume_parser` key)
- Write tests with mocked LLM responses
- **Output**: Upload resume → get list of structured career entries stored in DB with embeddings.

#### 2.3 — Career History UI (Frontend)
- Create career history page showing all parsed entries
- Entry card: title, organization, dates, bullet points, tags
- Edit entry inline (title, org, dates, bullets)
- Add new entry manually (form)
- Delete entry
- Reorder/reassign bullet points between entries (drag or manual)
- "Confirm all" button to mark entries as `user_confirmed`
- **Output**: User can view, edit, add, delete career history entries. Parsing Approval gate works.

#### 2.4 — Career History API Endpoints
- `GET /api/v1/career/entries` — list all entries for current user
- `POST /api/v1/career/entries` — create new entry
- `PUT /api/v1/career/entries/{id}` — update entry
- `DELETE /api/v1/career/entries/{id}` — delete entry
- All endpoints filter by `user_id` (data isolation)
- Regenerate embedding on entry update
- Write integration tests
- **Output**: Full CRUD on career history entries via API. Tests pass.

---

### Phase 3: Job Analysis & Matching

#### 3.1 — Job Analyst Agent
- Create LangGraph agent for JD parsing
- Define `JDAnalysis` Pydantic model (required skills, preferred skills, seniority, ATS keywords, tech stack, industry)
- Agent takes JD text → outputs structured `JDAnalysis`
- Store parsed JD in `job_descriptions` table with embedding
- Wire up model from config (`job_analyst` key)
- Write tests with sample JDs and mocked LLM
- **Output**: Paste a JD → get structured analysis stored in DB.

#### 3.2 — Entry Retrieval & Match Scoring
- Implement vector similarity search: JD embedding vs career entry embeddings (pgvector)
- Add tag-based filtering and recency boost
- Create match scoring logic: quantified score with category breakdown
- Rank and select top-K relevant entries
- Identify gaps (JD requirements not matched by any entry)
- Recommend section ordering based on relevance
- **Output**: Given a JD, return ranked career entries, match score, gaps, recommended structure.

#### 3.3 — Gate 1 UI (JD Analysis + Match Overview)
- Create session start flow: paste JD → show loading → show analysis
- Display: parsed JD requirements, match score, selected entries, gaps, recommended order
- Let user toggle entries on/off (include/exclude from resume)
- Let user add context via text input ("I also have experience with X")
- "Approve & Continue" button to proceed to resume writing
- Wire up `POST /api/v1/sessions/start` and `POST /api/v1/sessions/{id}/approve`
- **Output**: User pastes JD, sees analysis and match, adjusts selection, approves to continue.

---

### Phase 4: Resume Writer Agent (Core)

#### 4.1 — Resume Writer Agent (Basic)
- Create LangGraph agent for resume writing
- Agent takes: JD analysis + selected career entries + user preferences → outputs enhanced resume (structured JSON)
- Enhance summary/objective section
- Rewrite bullet points to highlight relevance to JD
- Reorder sections and bullets by relevance
- Tailor skills section
- Wire up model from config (`resume_writer` key)
- **Tools**: career history search, session context
- Write tests with mocked LLM
- **Output**: Given JD analysis + entries → get structured enhanced resume JSON.

#### 4.2 — Calibration Round (Gate 2)
- Implement calibration flow: writer produces first 2-3 bullets
- Frontend shows enhanced bullets with diff against originals
- User provides feedback (edit, style notes, approve)
- Feedback is incorporated into the writer agent's context for remaining bullets
- Writer completes the remaining bullets using learned style
- Wire up websocket for streaming bullet-by-bullet progress
- **Output**: User reviews first bullets, gives feedback, system completes rest matching the style.

#### 4.3 — Gate 3 UI (Full Draft Review with Per-Bullet Approval)
- Display complete enhanced resume
- Word-level diff for each bullet (original → enhanced)
- Per-bullet buttons: approve (✓), reject (✗), edit (pencil)
- Skills section with add/remove controls
- Section reorder controls (drag or up/down arrows)
- Collect all feedback and send back to writer agent for revision
- **Output**: User can review, approve/reject/edit every bullet in the enhanced resume.

#### 4.4 — LaTeX PDF Generation
- Create Jinja2 → LaTeX template (1 professional ATS-friendly template)
- LaTeX special character escaping for all user content
- Compile LaTeX → PDF using `tectonic` (inside Docker container)
- `GET /api/v1/resumes/{id}/pdf` endpoint
- Gate 4 UI: show PDF preview, "Generate PDF" button
- **Output**: Enhanced resume renders as a professional PDF. Download works.

#### 4.5 — WebSocket Streaming Infrastructure
- Set up WebSocket endpoint for session streaming (`WS /api/v1/sessions/{id}/stream`)
- Implement event protocol: `agent_start`, `agent_end`, `thinking`, `stream_token`, `progress`, `approval_gate`, `error`
- Wire LangGraph streaming callbacks to emit WebSocket events at each node transition and LLM token
- Frontend: connect to WebSocket, render streaming text, show agent activity indicator and progress
- **Output**: User sees real-time progress: which agent is active, tokens streaming, progress bars.

---

### Phase 5: Fact Checking & Chat

#### 5.1 — Fact Checker Agent
- Create LangGraph agent for fact verification
- Agent takes: enhanced resume + original career history → outputs verification report
- For each claim in the enhanced resume, find the source in career history or flag as unverified
- **Tools**: career history search (to look up backing evidence)
- Output structured report: `[{claim, source_entry_id, status: verified|unverified|modified, notes}]`
- Display fact-check flags as annotations at Gate 3
- **Output**: Enhanced resume bullets get verified/flagged badges. User sees what's backed by source.

#### 5.2 — Chat Agent
- Create LangGraph agent for freeform conversation
- Always available via chat panel (regardless of workflow state)
- Can answer questions about the JD, the resume, the enhancement process
- Can capture new information from the user and store as career history entries
- Can trigger re-entry to any previous gate
- **Tools**: all tools from other agents + session management
- `POST /api/v1/chat/message` and `WS /api/v1/chat/{session_id}/stream`
- **Output**: User can chat at any point. Agent answers, stores new info, routes to workflow steps.

#### 5.3 — Chat UI (Frontend)
- Chat panel component (sidebar or drawer)
- Message list with user/assistant bubbles
- Streaming response display (tokens appear in real-time)
- "Thinking" indicator with context message
- Input box with send button
- Chat is accessible from every page/gate in the workflow
- **Output**: Functional chat interface with streaming responses, available throughout the app.

---

### Phase 6: Review & Polish

#### 6.1 — Reviewer Agent
- Create LangGraph agent with two review perspectives
- Recruiter pass: scannability, impact, screening pass likelihood
- Hiring manager pass: technical depth, relevance, qualification signals
- **Tools**: career history search (cross-reference claims)
- Output structured feedback attached to specific sections/bullets
- Display reviewer annotations at Gate 3
- **Output**: Enhanced resume gets recruiter + HM feedback as annotations.

#### 6.2 — ATS Scoring
- Implement keyword match scoring (JD keywords vs resume content)
- Check section header formatting, date formats
- Light LLM call for keyword suggestions
- Display ATS score at Gate 3 and Gate 4
- **Output**: Resume gets an ATS score and actionable keyword suggestions.

#### 6.3 — Diff View Component (Frontend)
- Word-level diff rendering (original → enhanced)
- Color coding: green additions, red removals, yellow rephrasing
- Toggle between "changes only" and "full document" view
- Used at Gate 2 (calibration) and Gate 3 (full review)
- **Output**: Beautiful word-level diffs for every bullet point.

#### 6.4 — Cover Letter Generation
- Reuse Resume Writer Agent with a cover letter system prompt
- Input: JD analysis + matched career entries + company research (if available)
- Output: tailored cover letter maintaining user's voice
- Separate generation flow (button in the UI after resume is done, or concurrent)
- `POST /api/v1/cover-letter/generate`, `GET /api/v1/cover-letter/{id}`
- **Output**: User can generate a cover letter from the same session context.

#### 6.5 — Strength-of-Change Control
- Add slider/select in UI: conservative / moderate / aggressive
- Pass as parameter to Resume Writer Agent's system prompt
- Conservative: minor rephrasing, keyword insertion, reordering only
- Moderate (default): meaningful rewriting, active voice, quantification
- Aggressive: full restructure, significant rewording, may combine/split bullets
- Can be set per session; persists in session state
- **Output**: User controls how aggressively the resume is rewritten.

---

### Phase 7: Learning & History

#### 7.1 — Past Session Learning
- After session completion, store decisions in `session_decisions` table: JD embedding, selected entries, section order, style notes, user feedback summary
- On new session, retrieve top 2-3 similar past sessions by JD embedding + role title
- Inject past decisions as few-shot context for Resume Writer Agent
- Surface to user at Gate 1: "Based on your previous session for [similar role], I suggest these entries"
- **Output**: Second+ sessions for similar roles start with better defaults.

#### 7.2 — Version History
- Store each tailored resume as a versioned snapshot linked to the JD
- Version history page: list all past resumes with metadata (date, company, role, match score, ATS score)
- View any past version
- "Fork" a previous version as starting point for a new session
- **Output**: User can browse and reuse past resume versions.

#### 7.3 — Retrieval Quality Dashboard
- Simple page showing retrieval metrics:
  - User override rate at Gate 1 (how often user adds/removes entries)
  - Entry usage rate (fraction of retrieved entries in final resume)
  - Bullet rejection rate at Gate 3
- Helps the developer (you) decide when to invest in better retrieval
- **Output**: Dashboard showing how well the retrieval is serving the user.

---

### Phase 8: Extended Input & Templates

#### 8.1 — URL-Based JD Parsing
- Add URL input option to JD parsing flow
- Implement httpx + BeautifulSoup extraction for static pages
- Extract: title, company, location, requirements, responsibilities
- Fallback: if extraction fails, show raw text and let user paste manually
- Later: add Playwright for JS-rendered pages if needed
- **Output**: User can paste a URL instead of text for the JD.

#### 8.2 — Company Research Enrichment
- Web search tool for the Job Analyst Agent
- Search for: company values, tech stack, recent news, engineering blog
- Feed into cover letter and Resume Writer context
- Display company info at Gate 1
- **Output**: JD analysis includes company research when URL is provided.

#### 8.3 — Multiple LaTeX Templates
- Create 3-5 professional LaTeX resume templates
- Template selector at Gate 4 (final approval)
- Preview thumbnails for each template
- User can switch templates without re-running the enhancement
- Support user-uploaded LaTeX templates
- **Output**: User picks from multiple templates before PDF generation.

#### 8.4 — Multi-JD Mode
- Accept multiple JDs for the same role type
- Job Analyst produces a composite requirements profile (skills weighted by frequency across JDs)
- Single generalized resume optimized for the role, not one specific posting
- Composite profile stored for future refinement
- **Output**: User provides 3-5 JDs → gets one strong resume for the role category.

#### 8.5 — DOCX Export
- Convert structured resume JSON to DOCX via `python-docx`
- Match the styling of the selected LaTeX template as closely as possible
- `GET /api/v1/resumes/{id}/docx` endpoint
- **Output**: User can download resume as DOCX.

---

### Phase 9+: Future Features

These are planned but not broken into sub-phases yet. Each will be scoped when the time comes:

- **Interview Prep Mode**: generate practice questions + talking points from JD + resume context
- **LinkedIn Optimization**: analyze LinkedIn profile, suggest changes, show diff
- **Batch Apply Mode**: score multiple JDs, generate resumes in parallel, bulk export
- **Networking Outreach Drafts**: cold email, LinkedIn request, follow-up, referral templates
- **Quantification Assistant**: detect vague bullets, prompt for metrics, enrich career history
- **Advanced RAG**: add HyDE, cross-encoder re-ranking, multi-query retrieval (based on retrieval quality metrics)
- **Plain text export**: for copy-paste into online application forms

---

## 16. Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Language | Python 3.12+ | Ecosystem alignment with LangChain/LangGraph, FastAPI |
| Package manager | Poetry | Deterministic builds, dependency groups |
| Build automation | Makefile | Universal, CI-friendly |
| Database | PostgreSQL + pgvector | Single DB for structured + vector data |
| Agent framework | LangGraph | Human-in-the-loop, checkpointing, async support |
| PDF generation | LaTeX + Jinja2 | Proven professional output; user has existing templates |
| Web scraping | httpx + BS4 → Playwright | Start simple, add headless browser only when needed |
| Async processing | FastAPI native + LangGraph | No Celery until batch processing at scale |
| Frontend | Next.js (React + TypeScript) | Rich interactivity from day one; TypeScript for safety |
| UI components | shadcn/ui + Tailwind | Fast to build, beautiful defaults, accessible |
| Auth | JWT with refresh tokens | Stateless, standard |
| LLM config | YAML config with per-agent model mapping | Simple to change, no admin UI, full provider flexibility |
| RAG approach | Vector search + quality tracking → add complexity when measured | 5-30 entries is small; track metrics to know when to invest |
| Agents | 5 agents (Job Analyst, Resume Writer, Reviewer, Fact Checker, Chat) | Clear separation of concerns; each justified by tool/state needs; extensible |
| Approval flow | 5 gates (parsing → analysis → calibration → full draft → final) | Dedicated bullet-level review without waterfall overhead |
| Target audience | Family & friends | No monetization, no admin, no tiers |
| Phase sizing | Sub-phases sized for single Claude Code sessions | Incremental delivery; each sub-phase is self-contained |

---

## 17. Engineering Principles

### 17.1 Ship, Measure, Iterate
- Build the simplest version that delivers value. Measure what's actually broken. Fix that.
- Don't build the "model management platform" before you have users. Don't add HyDE before you know vector search is insufficient.
- Every feature has an implicit cost: code to maintain, bugs to fix, complexity to reason about.

### 17.2 Code Quality Standards
- Type hints on all function signatures. `mypy --strict`.
- Ruff for linting and formatting. Zero warnings in CI.
- Pre-commit hooks enforce quality before every commit.
- Pydantic models for all API schemas and internal data transfer.
- Tests alongside implementation. Minimum 80% coverage in CI.
- Mock external services in tests.

### 17.3 Project Structure
- Group by domain, not by layer (e.g., `agents/resume_writer/` not `services/`, `models/`, `controllers/`)
- Configuration via environment variables + Pydantic Settings
- All secrets in `.env` files (gitignored) or environment variables

### 17.4 Git & CI
- Conventional commits (`feat:`, `fix:`, `refactor:`, `docs:`, `test:`)
- Feature branches → PR → review → merge to main
- CI: lint → typecheck → test → build on every PR
- Pre-commit hooks: ruff format, ruff check, mypy

---

## Appendix A: v1 Review Notes

Key issues from v1 and how they were addressed:

| # | v1 Issue | v2 Resolution |
|---|---|---|
| 1 | 9 agents — over-engineering | 5 agents with clear justification; ATS scoring is a utility function |
| 2 | 10+ approval gates — unusable UX | 5 focused gates: parsing → analysis → calibration → full draft (per-bullet) → final |
| 3 | Advanced RAG before any data | Simple vector search + quality metrics from day one; add techniques based on evidence |
| 4 | Database-driven LLM model management platform | YAML config file with per-agent model mapping; no admin UI |
| 5 | Streamlit → React rewrite | Next.js from day one; detailed frontend guidance for non-JS developer |
| 6 | LaTeX risk (Unicode, errors, Docker size) | Kept LaTeX (user has templates, proven quality); mitigate with `tectonic` + input sanitization |
| 7 | "Single-shot resume after 3-5 sessions" | Reframed: system improves defaults over time; first session = big transform, subsequent = faster |
| 8 | Resume parsing hand-waved | Explicit LLM parsing strategy with user approval gate |
| 9 | Security misses real PII threat model | Realistic PII approach: accept LLM sends, document it, offer local model option |
| 10 | Phase 1 = 3-4 months | Split into 8 phases with ~35 sub-phases, each sized for a single Claude Code session |
| 11 | Missing deployment/monetization | Family & friends tool — no monetization, no deployment architecture needed yet |
| 12 | Celery + Redis premature | FastAPI native async + LangGraph; no Celery until batch processing at scale |
