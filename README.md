# GenAI Knowledge Platform

GenAI Knowledge Platform is a collaborative library for Generative AI learning material. Contributors add papers, guides, and notes; the platform reviews each resource before it becomes searchable, then answers questions from reviewed knowledge with supporting sources.

The project is designed as a focused, production-minded vertical slice: trustworthy ingestion, explainable publication decisions, and retrieval grounded in accepted content.

## Why this exists

Learning material about Generative AI changes quickly and is uneven in quality. A shared folder makes it easy to collect documents, but not to know whether they are relevant, readable, duplicated, or safe to rely on.

This platform treats publication as a decision, not a file-upload event. It helps a community build a smaller, more dependable knowledge base instead of an unreviewed document archive.

## Product flow

```text
Upload a resource
  → read and validate it
  → assess relevance and quality
  → check selected claims when needed
  → approve, reject, or request review
  → index accepted knowledge
  → answer questions from reviewed sources
```

Only approved resources participate in retrieval and answer generation.

## Key features

- Upload digital PDFs, Markdown, and plain-text resources.
- Enforce file type, MIME, size, page-count, readable-content, English-language, and GenAI-scope checks before expensive processing.
- Detect exact duplicates using a SHA-256 digest of the uploaded bytes.
- Parse digital PDFs offline with Docling; scanned and image-only PDFs fail safely instead of producing invented text.
- Route resources deterministically to approval, rejection, contributor review, or admin review.
- Let contributors accept or decline an unambiguous, deterministic correction before publication.
- Persist approved chunks and BGE embeddings in PostgreSQL with pgvector.
- Search approved knowledge with lexical and semantic retrieval, then generate an answer from the selected reviewed context.
- Present findings, review decisions, and grounded evidence without leaking provider payloads or internal implementation details.

## Knowledge Quality Engine

The Knowledge Quality Engine is the product’s decision boundary. It consumes normalized document content and returns structured findings; deterministic application code owns the resulting workflow state.

### Deterministic checks

- Supported extension and MIME type
- Maximum upload size and PDF page count
- Empty or insufficient extracted content
- English-language signal
- GenAI topic relevance
- Professional-profile versus learning-material detection
- Exact duplicate detection
- High-confidence mechanical corrections, such as an adjacent duplicated word

### Semantic checks

Gemini supplies structured analysis of the resource’s summary, topics, claims, and material semantic findings. The platform—not the model—maps that output to an explicit document state. Selected time-sensitive claims may be externally checked with Google Search Grounding; an unavailable grounding provider does not expose its error details to users.

### Publication states

| State | Meaning | Searchable |
| --- | --- | --- |
| `APPROVED` | Accepted and indexed | Yes |
| `CONTRIBUTOR_REVIEW_REQUIRED` | An unambiguous correction needs the contributor’s decision | Not yet |
| `ADMIN_REVIEW_REQUIRED` | A material issue requires closer review | No |
| `REJECTED` | The resource does not meet the platform’s requirements | No |
| `FAILED` | Processing could not finish safely | No |

## Architecture

```text
React + TypeScript
        │
        ▼
FastAPI modular monolith
  ├─ document ingestion and source storage
  ├─ Knowledge Quality Engine
  ├─ contributor review and publication
  ├─ Docling parsing and BGE embedding
  ├─ hybrid retrieval and answer generation
  └─ Gemini analysis and optional claim verification
        │
        ▼
PostgreSQL + pgvector
  ├─ document metadata and states
  ├─ structured findings and review decisions
  ├─ approved chunks
  └─ 384-dimensional embeddings
```

The backend is intentionally a modular monolith. It keeps data ownership, transaction boundaries, and state transitions easy to inspect while leaving clear seams for validators, retrieval, and model providers.

## Tech stack

| Area | Technology |
| --- | --- |
| Frontend | React 19, TypeScript, Vite, TanStack Query, react-dropzone, Framer Motion, Lucide, React Markdown |
| API | FastAPI, Pydantic v2, SQLModel, Alembic |
| Data | PostgreSQL 16, pgvector, PostgreSQL full-text search |
| Document processing | Docling, PyMuPDF |
| Retrieval | `BAAI/bge-small-en-v1.5`, pgvector cosine similarity, PostgreSQL full-text search |
| Reasoning and verification | Google GenAI SDK with configurable Gemini model and optional Google Search Grounding |
| Local runtime | Docker Compose, CPU-only PyTorch, offline Hugging Face caches |

## Repository structure

```text
.
├── backend/
│   ├── alembic/                 # Database migrations
│   ├── app/
│   │   ├── documents/           # Upload, parsing, storage, state, indexing
│   │   ├── knowledge_quality/   # Validators, findings, routing
│   │   ├── reviews/             # Contributor review decisions
│   │   ├── search/              # Retrieval and answer generation
│   │   ├── grounding/           # Normalized claim verification
│   │   ├── llm/                 # Gemini boundary and typed models
│   │   └── core/                # Configuration and error handling
│   └── tests/
├── frontend/
│   └── src/
│       ├── features/upload/
│       ├── features/search/
│       ├── api/
│       └── styles.css
├── docker-compose.yml
├── .env.example
└── AGENTS.md
```

## Local setup

### Prerequisites

- Docker Desktop with Docker Compose
- Node.js 20+ and pnpm (for the frontend)
- A Gemini API key for live semantic analysis and answer generation

### Configure environment

```bash
cp .env.example .env
```

Set `GEMINI_API_KEY` in `.env`. Keep this local file untracked.

### Start the backend and database

```bash
docker compose up --build -d
docker compose ps
```

The backend runs migrations at startup. Confirm readiness with:

```bash
curl http://localhost:8000/health/ready
```

### Start the frontend

```bash
cd frontend
pnpm install --frozen-lockfile
pnpm dev
```

Open [http://localhost:5173](http://localhost:5173). The API is available at [http://localhost:8000](http://localhost:8000), and interactive API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

## Docker runtime

The backend image is built for a CPU-only local runtime. During image construction it caches the BGE model and the Docling artifacts required for supported digital-PDF parsing. Runtime Hugging Face access is configured to remain offline.

Docker Compose persists two named volumes:

- `postgres_data` for PostgreSQL data
- `source_storage` for uploaded source files

Recreating the backend container does not delete either volume.

## Environment variables

Configuration is centralized in `backend/app/core/config.py`. `.env.example` contains the local defaults.

| Variable | Purpose |
| --- | --- |
| `GEMINI_API_KEY` | API key for Gemini analysis, answer generation, and optional verification |
| `GEMINI_MODEL` | Configurable Gemini model identifier |
| `DATABASE_URL` | PostgreSQL connection string |
| `FRONTEND_ORIGIN` | Allowed frontend origin for CORS |
| `MAX_UPLOAD_BYTES` | Maximum upload size |
| `MAX_PDF_PAGES` | Maximum allowed PDF pages |
| `MIN_MEANINGFUL_CHARACTERS` | Minimum useful extracted-content threshold |
| `GEMINI_TIMEOUT_SECONDS` | Provider request timeout |
| `GEMINI_MAX_RETRIES` | Bounded Gemini retry count |
| `PROCESSING_DELAY_SECONDS` | Optional local processing delay |

For the browser client, set `VITE_API_URL` only when the API is not at `http://localhost:8000`.

## Running the application

1. Start Docker Compose and wait for the backend readiness endpoint to return `{"status":"ok"}`.
2. Start the Vite frontend.
3. Add a PDF, Markdown, or text GenAI learning resource.
4. Follow the in-product review state until it reaches a terminal decision.
5. Search approved knowledge using a natural-language question.

## Demo walkthrough

Recommended reviewer path:

1. Open the landing page and inspect the upload requirements.
2. Upload a concise GenAI Markdown note with a clear explanation of Retrieval-Augmented Generation.
3. Watch the review state progress to an approval decision.
4. Search with a question such as: “How does retrieval-augmented generation help an LLM use context?”
5. Inspect the generated answer and supporting reviewed resources.
6. Upload an unrelated document to see the safe rejection path.
7. Upload a resource containing an obvious duplicated word to see the contributor-review decision.
8. Accept or decline the suggested mechanical correction and confirm that only the accepted document becomes searchable.
9. Upload the same accepted file again to see exact-duplicate protection.

## Design principles

- **Trust before discoverability.** A resource must earn its place in the library.
- **Deterministic workflow ownership.** Models contribute typed analysis; application code controls validation, routing, persistence, and state transitions.
- **Evidence over opaque confidence.** Findings and external references are presented as concise, inspectable information.
- **No silent rewrites.** A contributor must explicitly accept a proposed correction before it is published.
- **Calm, accessible product language.** The interface explains outcomes rather than implementation details, supports keyboard interaction, and respects reduced-motion preferences.
- **One datastore, simple operations.** PostgreSQL holds document state, source references, findings, chunks, and vectors.

## Engineering highlights

- Typed request, response, error, LLM, finding, and grounding boundaries.
- Explicit document-state transition rules prevent contradictory processing states.
- Transactional contributor decisions guard against repeated actions and duplicate indexing.
- Source storage is decoupled from container lifetime and survives backend recreation.
- Provider errors are classified and translated into safe user-facing messages.
- Grounded evidence is normalized and safelisted before reaching the API or UI.
- Retrieval queries filter at the database layer so non-approved material cannot be searched or used for answers.

## Limitations

- Supported uploads are limited to digital PDF, Markdown, and plain text; image-only and scanned PDFs are intentionally not accepted.
- Processing uses FastAPI background tasks for this exercise rather than a durable queue.
- Gemini availability and Google Search Grounding quotas are external operational dependencies.
- The current contributor-review scope is deliberately narrow: only deterministic, high-confidence mechanical corrections qualify.
- Search quality depends on the reviewed corpus; no answer is generated when retrieval finds no trusted knowledge.
- The application does not include authentication or multi-user authorization in this exercise scope.

## Future improvements

- Durable job execution and operational retry observability.
- Broader, evidence-backed contributor correction types with a source-level diff view.
- Retrieval evaluation datasets, ranking telemetry, and corpus-aware answer-quality measurements.
- Authenticated community workflows and moderator tools for admin-review decisions.
- Additional ingestion sources after equally strong validation and source-provenance handling.
- Production deployment configuration, monitoring, backup policy, and secret management.

## Quality checks

```bash
# Backend
cd backend
python3.12 -m ruff format --check .
python3.12 -m ruff check .
python3.12 -m mypy app
python3.12 -m pytest

# Frontend
cd ../frontend
pnpm format
pnpm lint
pnpm build

# Repository
git diff --check
```

---

Built as a focused engineering exercise in trustworthy GenAI knowledge ingestion, publication, and retrieval.
