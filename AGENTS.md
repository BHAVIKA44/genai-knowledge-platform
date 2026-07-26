````md
# AGENTS.md

## Purpose

This file defines the engineering contract for every AI agent working in this repository.

Read this file completely before making changes. Also read `decisions.md` before making architectural, product, infrastructure, or technology decisions.

The project must remain focused, production-minded, and achievable within a five-day engineering exercise. Do not expand the scope simply because an additional feature is technically possible.

The main principle is:

> Use mature libraries for solved problems. Invest custom engineering effort in the Knowledge Quality Engine.

---

# 1. Project Overview

This repository contains a collaborative Generative AI learning platform.

Users contribute GenAI learning resources such as:

- Research papers
- Technical PDFs
- Public documentation and blog URLs
- Markdown notes
- Plain-text notes
- Clear screenshots or images containing readable technical content

The platform converts these resources into structured and searchable knowledge.

Before any contribution becomes searchable, it passes through a **Knowledge Quality Engine** that evaluates whether the extracted knowledge is reliable enough to enter the shared knowledge base.

The Knowledge Quality Engine may detect:

- Poor extraction quality
- Missing information
- Exact duplicates
- Near-duplicate knowledge
- Contradictions
- Potentially outdated technical claims
- Missing evidence
- Claims that require external verification
- Unsupported or non-GenAI content

Approved knowledge is indexed using PostgreSQL Full-Text Search and pgvector. Users can then query the shared knowledge base using natural-language questions and receive answers with source citations.

---

# 2. Product Priorities

When trade-offs are required, use this order:

1. Correctness
2. User trust
3. Clear failure handling
4. Knowledge Quality Engine depth
5. Maintainability
6. Testability
7. Setup and deployment reliability
8. User experience
9. Performance at expected project scale
10. Additional features

Never sacrifice the correctness or explainability of the Knowledge Quality Engine to add more pages, dashboards, integrations, or visual effects.

---

# 3. Core Engineering Philosophy

## 3.1 Build the differentiator, not the infrastructure

The differentiator is the **Knowledge Quality Engine**.

Do not spend significant custom engineering effort rebuilding:

- Document parsing
- OCR engines
- Embedding models
- Vector storage
- Form libraries
- UI component libraries
- Database migrations
- Background job systems
- HTTP clients
- Retry frameworks
- Logging frameworks

Use mature libraries for these concerns.

Custom code should primarily implement:

- Knowledge validation rules
- Issue classification
- Evidence evaluation
- Confidence aggregation
- Contradiction detection
- Review routing
- Publication decisions
- User-facing explanations
- Knowledge-quality-aware retrieval behavior

---

## 3.2 LLMs provide intelligence, not orchestration

The LLM may perform tasks requiring semantic understanding or judgment.

Examples:

- Extracting structured knowledge
- Identifying claims
- Detecting semantic contradictions
- Evaluating whether a claim may be outdated
- Explaining why a claim was flagged
- Suggesting a correction
- Evaluating external evidence

The LLM must not control application workflow.

Deterministic application code must own:

- File validation
- MIME validation
- Size limits
- Duplicate file detection
- Retry policies
- Timeouts
- State transitions
- Queue behavior
- Confidence thresholds
- Publication routing
- Permissions
- Database updates
- Search filtering
- Error classification

The model provides structured findings and evidence. The application makes the final decision.

---

## 3.3 Prefer deterministic logic whenever possible

Do not ask an LLM to solve a problem that regular code can solve reliably.

Use deterministic code for:

- SHA-256 hashing
- URL normalization
- File-size validation
- Page-count validation
- Empty document detection
- Character-count validation
- MIME and extension checks
- State transitions
- Score thresholds
- Required-field validation
- Retry rules
- Search access rules
- Approved-versus-pending filtering
- Exact duplicate detection

Use AI only when semantic understanding is required.

---

## 3.4 Keep the architecture simple

Prefer a modular monolith.

Do not introduce:

- Microservices
- Event buses
- Kafka
- Kubernetes
- Generic plugin frameworks
- Distributed workflow engines
- Multiple databases
- Custom vector databases
- A general-purpose rule engine
- Deep inheritance hierarchies

The system should remain understandable by one engineer reading the repository.

---

## 3.5 Design for likely change, not hypothetical change

The code should be extensible where change is realistic.

Likely extension points include:

- Adding a new knowledge validator
- Replacing the LLM provider
- Supporting a new document source
- Adding a retrieval ranking strategy
- Adding a review-routing rule
- Supporting another embedding model

Do not add interfaces or factories for components that have no realistic second implementation.

Extensibility should come from:

- Clear module boundaries
- Small public APIs
- Composition
- Typed domain models
- Dependency injection at infrastructure boundaries

It should not come from speculative abstraction.

---

# 4. Approved Technology Stack

Use the following stack unless `decisions.md` is explicitly updated.

## Frontend

- React 19
- TypeScript
- Vite
- Tailwind CSS
- shadcn/ui
- TanStack Query
- TanStack Table
- React Router
- React Hook Form
- Zod
- react-dropzone
- Sonner
- Lucide React
- Framer Motion, used sparingly
- React Markdown for rendered knowledge content
- A PDF viewer library only where source inspection requires it

## Backend

- Python 3.12
- FastAPI
- Pydantic v2
- pydantic-settings
- SQLModel
- Alembic
- PostgreSQL
- pgvector
- Docling
- Sentence Transformers
- `BAAI/bge-small-en-v1.5`
- Gemini 2.5 Flash
- Gemini Google Search Grounding
- ARQ and Redis for background jobs, only if the asynchronous workflow is implemented
- structlog
- pytest
- pytest-asyncio
- pytest-mock
- Ruff
- mypy

## Deployment

- Frontend: Vercel
- Backend: Docker container on a service with sufficient memory for Docling
- Database: Managed PostgreSQL with pgvector support
- Redis: Managed Redis only if ARQ is retained
- Minimum backend memory target: 2 GB
- Preferred backend memory target: 4 GB

Do not replace these choices casually. Record any meaningful change in `decisions.md`.

---

# 5. Library-First Development Rules

Before writing custom infrastructure code, check whether the chosen library already provides the required capability.

Use:

- **Docling** for parsing, OCR integration, reading order, layout handling, tables, and document normalization.
- **Pydantic** for request, response, configuration, and LLM-output validation.
- **SQLModel and SQLAlchemy capabilities** for persistence.
- **Alembic** for migrations.
- **Sentence Transformers** for local embeddings.
- **pgvector** for vector persistence and nearest-neighbor retrieval.
- **PostgreSQL `tsvector`** for full-text search.
- **TanStack Query** for server state.
- **React Hook Form and Zod** for form behavior and client-side validation.
- **shadcn/ui** for accessible UI primitives.
- **react-dropzone** for upload interactions.
- **Sonner** for toast notifications.
- **Lucide** for icons.
- **Framer Motion** only for purposeful motion.

Do not create custom replacements for these capabilities unless a concrete limitation is demonstrated.

Before adding a dependency, ask:

> Does this library remove meaningful complexity, or am I adding a dependency to avoid writing a small amount of straightforward code?

Every dependency must justify its operational and maintenance cost.

---

# 6. Repository Structure

Use a feature-oriented structure.

Avoid generic folders such as:

- `helpers`
- `misc`
- `managers`
- `processors`
- `common_utils`

A recommended high-level structure is:

```text
.
├── AGENTS.md
├── README.md
├── decisions.md
├── .env.example
├── docker-compose.yml
├── backend/
│   ├── Dockerfile
│   ├── pyproject.toml
│   ├── alembic.ini
│   ├── alembic/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   ├── logging.py
│   │   │   ├── errors.py
│   │   │   └── dependencies.py
│   │   ├── db/
│   │   │   ├── session.py
│   │   │   └── migrations-related helpers only if needed
│   │   ├── documents/
│   │   │   ├── routes.py
│   │   │   ├── schemas.py
│   │   │   ├── models.py
│   │   │   ├── service.py
│   │   │   ├── ingestion.py
│   │   │   └── repository.py only when explicit queries benefit from it
│   │   ├── knowledge_quality/
│   │   │   ├── engine.py
│   │   │   ├── models.py
│   │   │   ├── scoring.py
│   │   │   ├── routing.py
│   │   │   ├── validators/
│   │   │   │   ├── metadata.py
│   │   │   │   ├── extraction_quality.py
│   │   │   │   ├── duplicates.py
│   │   │   │   ├── contradictions.py
│   │   │   │   ├── citations.py
│   │   │   │   └── freshness.py
│   │   │   └── prompts/
│   │   ├── reviews/
│   │   │   ├── routes.py
│   │   │   ├── schemas.py
│   │   │   ├── models.py
│   │   │   └── service.py
│   │   ├── search/
│   │   │   ├── routes.py
│   │   │   ├── schemas.py
│   │   │   ├── embeddings.py
│   │   │   ├── retrieval.py
│   │   │   ├── ranking.py
│   │   │   └── answering.py
│   │   ├── llm/
│   │   │   ├── client.py
│   │   │   ├── schemas.py
│   │   │   └── grounding.py
│   │   └── workers/
│   │       ├── settings.py
│   │       └── jobs.py
│   └── tests/
│       ├── unit/
│       ├── integration/
│       ├── api/
│       ├── fixtures/
│       └── samples/
└── frontend/
    ├── src/
    │   ├── app/
    │   ├── components/
    │   │   └── ui/
    │   ├── features/
    │   │   ├── upload/
    │   │   ├── processing/
    │   │   ├── knowledge/
    │   │   ├── search/
    │   │   └── review/
    │   ├── lib/
    │   ├── routes/
    │   ├── styles/
    │   └── main.tsx
    └── tests/
````

This structure is guidance, not a mandate. Do not create empty folders for hypothetical code.

Create a module only when the corresponding functionality exists.

---

# 7. Backend Engineering Rules

## 7.1 Thin API routes

Route handlers should:

1. Validate input.
2. Resolve dependencies.
3. Call one application service.
4. Translate known domain errors into API responses.
5. Return a typed response.

Routes must not contain:

* Knowledge validation rules
* LLM prompt logic
* Database query construction
* Publication decisions
* File parsing
* Embedding generation

---

## 7.2 Business logic belongs in explicit services

Application services should coordinate domain operations.

Examples:

* `DocumentIngestionService`
* `KnowledgeQualityEngine`
* `ReviewService`
* `HybridSearchService`
* `AnswerGenerationService`

Do not create a universal `BaseService`.

Do not place unrelated responsibilities in one service.

---

## 7.3 The Knowledge Quality Engine must remain independently testable

The engine should consume typed domain input and produce typed validation output.

It should not directly know:

* HTTP
* FastAPI
* PostgreSQL connection details
* Redis protocol details
* UI concerns
* Raw Gemini SDK response objects
* Raw Docling implementation objects

Convert infrastructure output into stable domain models before passing it to the engine.

---

## 7.4 Use composition for validators

The engine should compose focused validators.

Example:

```python
validators = [
    ExtractionQualityValidator(),
    MetadataValidator(),
    DuplicateValidator(),
    ContradictionValidator(),
    CitationValidator(),
    FreshnessValidator(),
]
```

A validator should return structured findings.

Do not build a large inheritance tree or plugin framework.

Adding a validator should require minimal changes to existing validators.

---

## 7.5 Do not use a generic repository framework

SQLModel already abstracts common database work.

Prefer explicit, readable queries.

Introduce a small repository only when it:

* Centralizes a meaningful query
* Prevents query duplication
* Is independently testable
* Represents a clear persistence boundary

Do not add:

* `BaseRepository`
* `GenericRepository`
* Generic CRUD abstractions
* Repositories that merely wrap one-line ORM calls

---

## 7.6 Use transactions for multi-step state changes

Operations that must succeed or fail together belong in a transaction.

Examples:

* Approving a review and publishing knowledge
* Persisting a document, chunks, and validation status
* Rejecting a submission and updating its review task

Do not leave partially published knowledge.

---

## 7.7 Make invalid states impossible

Represent document processing with explicit states.

Possible states may include:

```text
UPLOADED
QUEUED
PARSING
EXTRACTING
VALIDATING
CONTRIBUTOR_REVIEW_REQUIRED
ADMIN_REVIEW_REQUIRED
APPROVED
REJECTED
FAILED
```

Do not use multiple booleans such as:

* `is_approved`
* `needs_review`
* `is_failed`
* `is_processing`

when they can create contradictory combinations.

Validate allowed state transitions in deterministic code.

---

## 7.8 Use typed domain errors

Do not raise generic `Exception` or misuse `ValueError` for business failures.

Use meaningful errors such as:

* `UnsupportedFileTypeError`
* `FileTooLargeError`
* `DocumentTooLongError`
* `EmptyDocumentError`
* `DuplicateSubmissionError`
* `UnreadableDocumentError`
* `UnsupportedLanguageError`
* `NonGenAIContentError`
* `ExternalVerificationUnavailableError`
* `InvalidStateTransitionError`

Map domain errors to consistent API error responses.

---

## 7.9 Configuration must be centralized

Use `pydantic-settings`.

Centralize:

* Supported extensions
* Accepted MIME types
* Maximum file size
* Maximum page count
* Maximum image size
* Minimum extracted character count
* URL timeout
* Maximum redirects
* Confidence thresholds
* Retry counts
* Gemini model name
* Embedding model name
* Chunk configuration
* Search result limits
* Database URL
* Redis URL

Do not scatter constants throughout the codebase.

---

# 8. AI and LLM Rules

## 8.1 Use Gemini 2.5 Flash as the primary reasoning model

Use Gemini for:

* Structured knowledge extraction
* Topic and entity identification
* Claim extraction
* Contradiction analysis
* Freshness analysis
* Suggested corrections
* Human-readable explanations
* Grounded external verification

Do not use Gemini for:

* File validation
* Workflow state
* Retry policy
* Hashing
* Database decisions
* Upload constraints
* Publication threshold evaluation

---

## 8.2 All LLM outputs must be structured

Every LLM response must conform to a Pydantic schema.

Never parse free-form prose with regular expressions.

Never allow raw LLM output to update the database.

The sequence must be:

```text
LLM response
→ schema validation
→ deterministic application validation
→ domain model
→ business decision
```

Malformed output should be retried only according to the configured retry policy.

After retries are exhausted, route the submission safely to review or failure handling.

---

## 8.3 Do not request or expose hidden chain-of-thought

The application should request:

* Findings
* Evidence
* Concise explanations
* Confidence
* Suggested action

Do not request private reasoning traces.

Users should see evidence-backed explanations, not hidden internal reasoning.

---

## 8.4 External grounding must be selective

Do not invoke Google Search Grounding for every sentence or every upload.

Grounding is appropriate for claims involving:

* Current API behavior
* Recent model releases
* Framework ownership
* Version-specific capabilities
* Deprecations
* Rapidly changing GenAI facts
* Claims conflicting with approved knowledge

Grounding is not required for:

* File metadata
* Duplicate detection
* OCR quality
* Missing title
* Empty content
* Schema completeness

---

## 8.5 Treat grounded results as evidence, not absolute truth

The system must not claim universal factual certainty.

Grounded findings should include:

* Source URLs or citations
* Source titles
* Evidence snippets where permitted
* Confidence
* A clear verdict or uncertainty status

When evidence is weak or conflicting, route the item for human review.

---

## 8.6 AI must not silently rewrite user content

Suggested corrections must be shown to the contributor.

The system may:

* Propose a correction
* Explain the issue
* Provide supporting evidence
* Ask for acceptance

The system must not silently modify or publish altered contributor content.

---

# 9. Document Ingestion Rules

## 9.1 Supported scope

The first version supports English-language GenAI learning resources in:

* PDF
* DOCX, only if retained in the final product scope
* Markdown
* Plain text
* PNG
* JPEG
* Public HTML/documentation URLs

Do not imply that the platform accepts arbitrary content or every document type.

---

## 9.2 Validate before expensive processing

Before Docling, embeddings, or Gemini calls, validate:

* File extension
* MIME type
* File size
* Empty byte stream
* Duplicate SHA-256 hash
* Duplicate normalized URL
* Supported URL scheme
* Existing queued or processed submission

Reject invalid input early.

---

## 9.3 Product limits

Use the configured limits from one source of truth.

Current intended limits:

* Maximum file size: 50 MB
* Maximum document length: 250 pages
* Maximum individual image size: 10 MB
* Maximum concurrent uploads per user: 5
* Minimum extracted content: 50 meaningful characters
* Maximum processing duration must be bounded
* Maximum generated chunks must be bounded internally

Do not expose implementation concepts such as chunk limits to users.

Translate them into product language such as:

> This document is larger than the current processing limit. Please split it into smaller documents.

---

## 9.4 MIME verification

Do not trust file extensions.

Verify MIME type and perform a basic stream/header inspection.

Reject binary executables or unrelated payloads renamed as:

* `.txt`
* `.md`
* `.pdf`
* `.jpg`

Do not claim full malware scanning.

Enterprise malware scanning is outside the project scope.

---

## 9.5 Empty document handling

Reject:

* Zero-byte files
* Whitespace-only text
* Documents producing zero textual tokens
* Documents producing fewer than the configured minimum meaningful characters

Do not send empty documents to embeddings or Gemini.

---

## 9.6 Duplicate handling

For files:

* Compute SHA-256 before expensive processing.
* Check both completed records and active processing jobs.

For URLs:

* Normalize scheme, host, trailing slash, fragments, and common tracking parameters.
* Check for an existing normalized URL.

Return an idempotent, friendly response.

Do not launch duplicate processing jobs.

---

## 9.7 URL ingestion constraints

For public URLs:

* Allow only `http` and `https`
* Use a strict request timeout
* Follow at most two redirects
* Reject authentication-protected pages
* Reject paywalls
* Reject anti-bot challenge pages
* Handle 403, 404, 429, 500, and timeout responses
* Do not crawl entire websites
* Do not bypass robots, authentication, or access restrictions
* Protect against server-side request forgery by blocking private and local network targets

A failed URL ingestion should produce an actionable message.

---

## 9.8 Poor document quality

If extraction is unreliable:

* Do not invent missing text.
* Do not continue silently.
* Do not publish low-quality knowledge.

Return guidance such as:

> We could not reliably read this document. Please upload a clearer image or the original digital PDF.

Log technical details internally.

---

## 9.9 Partial parsing

Process partial documents only when Docling returns sufficiently reliable page-level output and missing pages are clearly identifiable.

If partial processing is supported:

* Record affected pages.
* Inform the user.
* Require review before publication.

Do not claim complete extraction when pages failed.

If partial parsing cannot be made reliable within the project timeline, reject the document gracefully instead.

---

## 9.10 Filename safety

Never use the original filename as a storage path.

* Generate an internal UUID.
* Sanitize display filenames.
* Prevent path traversal.
* Preserve the original display name as metadata only.

---

# 10. Knowledge Quality Engine Rules

## 10.1 The engine is the primary custom subsystem

Most custom design and testing effort belongs here.

The engine must remain:

* Modular
* Explicit
* Explainable
* Deterministic where possible
* Independently testable
* Easy to extend with new validators

---

## 10.2 Validation findings must be structured

Each finding should include fields such as:

```text
code
category
severity
confidence
title
explanation
evidence
suggested_action
suggested_correction
requires_external_verification
```

Do not return only a boolean or one overall score.

---

## 10.3 Quality score is an operational signal

The Knowledge Quality Score must not be presented as an objective truth probability.

It may aggregate:

* Extraction quality
* Metadata completeness
* Duplicate similarity
* Contradiction severity
* Citation quality
* Source evidence
* Freshness concerns
* Model confidence

Document the scoring method.

Do not use unexplained or arbitrary weights.

Prefer simple, defensible scoring over false mathematical precision.

---

## 10.4 Workflow decisions remain deterministic

The routing engine should use explicit rules.

Example:

```text
No blocking issues + high confidence
→ Auto publish

Correctable high-confidence issue
→ Contributor review

Ambiguous or externally disputed issue
→ Admin review

Unreadable, unsupported, or invalid input
→ Reject before publication
```

Threshold values must be centralized and testable.

---

## 10.5 Duplicate detection should have two levels

### Exact duplicate

Use:

* SHA-256 for files
* Normalized URL for webpages

### Semantic near duplicate

Use embeddings or approved knowledge comparison.

Near duplicates should be flagged, not automatically rejected, unless the product rule explicitly supports automatic merging.

Do not merge knowledge silently.

---

## 10.6 Contradiction detection must preserve evidence

A contradiction finding should identify:

* The new claim
* The existing approved claim
* Their source documents
* Why they appear inconsistent
* External evidence if grounding was used
* Confidence
* Recommended review action

Do not replace existing approved knowledge automatically.

---

## 10.7 Domain validation

The platform supports GenAI learning resources only.

A domain-relevance check may classify uploads as:

* Relevant
* Uncertain
* Unrelated

Uncertain content should not be rejected solely on weak model confidence. Route it for review when appropriate.

Unrelated content should receive a clear message explaining the platform scope.

---

# 11. Search and Retrieval Rules

## 11.1 Use one datastore

Use PostgreSQL for:

* Relational metadata
* Document status
* Knowledge chunks
* Full-text indexes
* Embeddings
* Review state

Do not introduce Pinecone, Qdrant, Weaviate, Elasticsearch, or another datastore without an explicit new requirement.

---

## 11.2 Embedding model

Use:

```text
BAAI/bge-small-en-v1.5
```

Store 384-dimensional vectors.

Pre-download the model during Docker image construction.

Do not depend on Hugging Face network availability at application startup.

Configure a persistent model-cache path.

---

## 11.3 BGE asymmetric retrieval behavior

Document chunks are embedded without a query prefix.

User search queries must use the model-recommended retrieval instruction:

```text
Represent this sentence for searching relevant passages:
```

Keep this behavior in one embedding service so it cannot be inconsistently applied.

---

## 11.4 Vector indexing

Use pgvector cosine distance.

Use an HNSW index with `vector_cosine_ops` when the migration is implemented.

Do not optimize ANN parameters without measurement.

At small scale, correctness matters more than benchmark tuning.

---

## 11.5 Hybrid search

Combine:

* PostgreSQL Full-Text Search
* pgvector semantic retrieval

Merge ranked results using Reciprocal Rank Fusion.

Do not directly add incompatible lexical and vector similarity scores.

Keep ranking logic explicit and tested.

---

## 11.6 Search only approved knowledge

Search and answer generation must exclude:

* Pending submissions
* Rejected documents
* Failed documents
* Contributor drafts
* Unapproved corrections

Enforce this at the database query level, not only in the frontend.

---

## 11.7 Answers require evidence

Every generated answer must include supporting approved sources.

If retrieval does not produce sufficient evidence:

* Do not fabricate an answer.
* State that the knowledge base does not contain enough trusted information.
* Suggest a broader query or additional contribution.

---

# 12. Background Processing Rules

Document processing is long-running and should not block the upload request.

The intended sequence is:

```text
Upload accepted
→ Job queued
→ Parsing
→ Extraction
→ Quality validation
→ Optional grounding
→ Embedding
→ Indexing
→ Review or publication
```

The API should return a document/job identifier quickly.

Use polling or a lightweight status mechanism unless streaming provides clear value.

Do not implement WebSockets only for visual novelty.

If ARQ and Redis add more complexity than value during the first vertical slice, start with a replaceable background-job boundary and document the decision. Do not pretend FastAPI `BackgroundTasks` is a durable production queue.

Jobs should be idempotent where practical.

Retries must be bounded.

Do not retry:

* Unsupported files
* Empty documents
* Invalid MIME types
* Non-GenAI content confirmed with high confidence

Retry transient failures such as:

* Gemini timeout
* Temporary database issue
* Temporary external URL failure
* Temporary embedding-model failure

---

# 13. API Design Rules

## 13.1 Typed contracts

Every request and response must use Pydantic models.

Do not return unstructured dictionaries from routes.

---

## 13.2 Consistent error envelope

Use one error-response shape.

Example:

```json
{
  "error": {
    "code": "DOCUMENT_TOO_LARGE",
    "message": "This document is larger than the current 50 MB upload limit.",
    "action": "Please compress the file or split it into smaller documents.",
    "request_id": "..."
  }
}
```

User-facing messages must not expose infrastructure details.

---

## 13.3 Appropriate HTTP semantics

Use meaningful status codes, but do not force users to understand them.

Examples:

* `400` for invalid input
* `409` for duplicate submission or invalid state conflict
* `413` for upload size
* `415` for unsupported media type
* `422` for schema validation
* `429` for rate or concurrency limits
* `503` for temporary dependency failure

The UI should translate these into plain language.

---

## 13.4 Idempotency

Duplicate uploads should not create duplicate processing jobs.

Review actions must guard against repeated submissions.

Where relevant, use transaction checks or idempotency keys.

---

# 14. Frontend Engineering Rules

## 14.1 Build the product, not a UI framework

Use existing libraries for:

* Buttons
* Dialogs
* Sheets
* Tables
* Tooltips
* Forms
* Toasts
* Drag and drop
* Focus management
* Keyboard interactions
* Loading primitives

Do not build a custom design system.

Use shadcn/ui as accessible primitives, then apply a consistent product style.

---

## 14.2 AI-native visual language

The interface should feel:

* Modern
* Technical
* Calm
* Premium
* Minimal
* Typography-led
* Motion-aware
* Spacious

The visual direction may draw inspiration from modern AI products such as Zamp, Linear, Vercel, OpenAI, Anthropic, and Arc, but must not copy their branding or layouts.

Use:

* Strong typography
* Generous whitespace
* Minimal borders
* Subtle depth
* Dark-first presentation if it serves readability
* Limited accent colors
* Purposeful gradients only when appropriate
* Clear hierarchy

Avoid generic admin-dashboard aesthetics.

---

## 14.3 Minimalism with progressive disclosure

Every screen should have one primary purpose.

Do not show all metadata, evidence, model details, and controls at once.

Examples:

* Show the quality status first.
* Reveal detailed findings on demand.
* Show evidence inside an expandable panel or drawer.
* Keep technical metadata in a secondary view.
* Keep upload constraints visible but concise.

---

## 14.4 Motion must communicate state

Use Framer Motion only when motion:

* Communicates workflow progression
* Reinforces an action
* Connects two interface states
* Reduces perceived waiting time
* Provides a rare moment of delight

Do not animate every card or button.

Do not use motion that delays interaction.

---

## 14.5 Moments of delight through restraint

Small playful moments are allowed.

Examples:

* A subtle knowledge orb that changes state
* A brief celebration on the first approved contribution
* A friendly message during long validation
* A small animation when a high-quality knowledge item is published

These moments must be:

* Infrequent
* Non-blocking
* Accessible
* Easy to remove
* Consistent with the product

Do not create a mascot system, game mechanics, or distracting animation layer.

---

## 14.6 Use business-oriented component names

Prefer:

* `KnowledgeUploadPanel`
* `ValidationTimeline`
* `QualityFindingCard`
* `EvidenceDrawer`
* `ReviewDecisionPanel`
* `KnowledgeSearchResult`
* `SourceViewer`

Avoid:

* `Card1`
* `MainWidget`
* `BigModal`
* `DataBox`
* `GenericSection`

---

## 14.7 Keep business logic out of components

React components should primarily render state and dispatch user actions.

Use feature hooks and API modules for:

* Upload mutation
* Processing status
* Search requests
* Review actions
* Query invalidation

Do not reproduce backend quality rules in the browser.

Client validation should improve UX, not become a second source of business truth.

---

## 14.8 Distinguish server state from UI state

TanStack Query owns:

* Documents
* Job status
* Validation results
* Review queue
* Search results
* Knowledge records

Local React state owns:

* Open dialogs
* Selected tabs
* Expanded sections
* Temporary input
* Local presentation choices

Do not copy server responses into local state without a concrete reason.

---

## 14.9 Upload constraints must be visible before upload

Near the upload area, show concise guidance:

* Supported formats
* Maximum file size
* Maximum page count
* English only
* GenAI learning resources only
* Public URLs only
* Clear images recommended

Provide a secondary “Upload guidelines” dialog for complete details.

Do not make users discover constraints after waiting for processing.

---

## 14.10 Design all application states

Every data-driven component must account for:

* Initial state
* Loading state
* Success state
* Empty state
* Partial state
* Error state
* Retry state
* Disabled state

Do not leave blank screens.

---

## 14.11 No technical error messages

Never display:

* Stack traces
* SQL errors
* Provider error messages
* JSON parsing failures
* OCR library names
* Embedding failures
* Redis failures
* HTTP codes without explanation

Translate them into plain, actionable language.

---

## 14.12 Accessibility

Use semantic HTML and accessible primitives.

Maintain:

* Keyboard navigation
* Visible focus
* Correct labels
* ARIA only where needed
* Sufficient contrast
* Reduced-motion support
* Screen-reader-friendly status updates

Do not sacrifice accessibility for visual style.

---

## 14.13 Performance

Lazy-load heavy experiences such as:

* PDF viewer
* Source viewer
* Large markdown renderer

Avoid unnecessary global state.

Use list virtualization only when actual list size justifies it.

Do not optimize without measurement.

---

# 15. Code Quality Rules

## 15.1 Code must not look machine-generated

AI-assisted code is a first draft.

Before completing a task:

* Remove tutorial-style comments.
* Remove comments that repeat the code.
* Remove generic abstractions.
* Rename vague identifiers.
* Remove dead branches.
* Remove unused helpers.
* Remove placeholder TODOs.
* Remove speculative features.
* Ensure conventions match nearby code.
* Review the complete diff manually.

The final code should feel intentionally written for this repository.

---

## 15.2 Comments explain why, not what

Bad:

```python
# Increment retry count
retry_count += 1
```

Good:

```python
# Grounded requests consume a limited quota, so retries remain intentionally bounded.
```

Use comments for:

* Non-obvious business reasoning
* Workarounds for library limitations
* Security constraints
* Trade-offs
* Unexpected edge-case behavior

Prefer self-explanatory code for everything else.

---

## 15.3 Naming is part of design

Use names that describe business meaning.

Prefer:

* `route_validation_result`
* `calculate_quality_score`
* `find_semantic_duplicates`
* `publish_approved_knowledge`

Avoid:

* `handle_data`
* `process_item`
* `do_check`
* `manager`
* `helper`
* `utils2`

---

## 15.4 Avoid deep nesting

Use guard clauses and early returns.

Functions should present the happy path clearly.

---

## 15.5 Keep functions cohesive

A function should perform one logical operation.

Do not enforce an arbitrary line limit, but split functions when they require multiple levels of explanation or mix unrelated responsibilities.

---

## 15.6 DRY is not a reason for premature abstraction

Avoid harmful duplication, especially for:

* Business rules
* Configuration
* SQL query logic
* Error formats
* State-transition logic

Small, coincidental duplication may be clearer than a generic abstraction.

Abstract only when a stable shared concept exists.

---

## 15.7 SOLID is guidance, not ceremony

Apply SOLID where it improves the project.

* Single Responsibility: yes.
* Composition over inheritance: yes.
* Dependency inversion at external provider boundaries: yes.
* Interface for every class: no.
* Abstract factory for one implementation: no.

Do not force patterns into simple code.

---

## 15.8 Keep public APIs small

Expose only methods required by other modules.

Implementation details should remain private to their feature.

---

## 15.9 No dead or commented-out code

Version control stores history.

Delete abandoned code rather than commenting it out.

---

## 15.10 Formatting and typing

Backend:

* Ruff formatting and linting
* mypy for meaningful type checking
* Type annotations on public functions and domain boundaries

Frontend:

* ESLint
* Prettier
* TypeScript strict mode

Do not silence errors broadly.

Use targeted ignores only with a clear reason.

---

# 16. Security and Privacy Rules

* Never commit secrets.
* Maintain `.env.example`.
* Validate all uploads server-side.
* Sanitize filenames.
* Block path traversal.
* Protect URL ingestion against SSRF.
* Set HTTP-client timeouts.
* Limit redirects.
* Do not fetch private network addresses.
* Do not expose Gemini keys to the frontend.
* Do not log document contents unnecessarily.
* Do not log secrets, tokens, database URLs, or credentials.
* Use parameterized ORM queries.
* Restrict CORS to configured origins.
* Apply upload and concurrency limits.
* Search only approved records.
* Treat uploaded documents as untrusted input.

Do not claim enterprise compliance such as SOC 2, HIPAA, or GDPR readiness.

---

# 17. Logging and Observability

Use structured logging.

Each request and background job should carry identifiers such as:

* Request ID
* Job ID
* Document ID
* User or contributor ID where available

Track business events:

* Upload accepted
* Upload rejected
* Duplicate detected
* Parsing started and completed
* Extraction started and completed
* Grounding invoked
* Quality validation completed
* Review requested
* Knowledge approved
* Knowledge rejected
* Indexing completed
* Search completed

Record durations for:

* Upload
* Parsing
* OCR
* LLM extraction
* Grounding
* Embedding
* Quality validation
* Search
* Answer generation

Do not log:

* Secrets
* Raw API keys
* Full private documents
* Unnecessary prompt content
* Sensitive headers

User-facing errors and internal logs must be separate.

---

# 18. Testing Philosophy

Tests protect user trust. They do not exist to inflate coverage.

Ask:

> If this behavior breaks in production, would I want a test to catch it first?

Test behavior, contracts, business rules, state transitions, and realistic failure modes.

Do not test framework internals.

---

## 18.1 Highest-priority test areas

### Knowledge Quality Engine

Test:

* Exact duplicates
* Near duplicates
* Missing metadata
* Contradiction findings
* Citation findings
* Freshness findings
* Quality score behavior
* Review routing
* Auto-publication boundaries
* Ambiguous evidence
* Malformed model output
* Conflicting grounded sources

### Ingestion

Test:

* Empty file
* Whitespace-only file
* File below minimum useful content
* Unsupported extension
* MIME mismatch
* Binary renamed as text
* Oversized file
* Too many pages
* Duplicate active job
* Duplicate completed upload
* Corrupted PDF
* Unreadable image
* Unsupported language
* Non-GenAI content
* URL timeout
* Redirect limit
* 403
* 404
* 429
* Anti-bot page
* Private-network URL

### Workflow

Test:

* Valid state transitions
* Invalid state transitions
* Retry behavior
* Job idempotency
* Contributor review
* Admin approval
* Admin rejection
* Duplicate review submission
* Failed persistence rollback

### Search

Test:

* Approved-only filtering
* Exact keyword retrieval
* Semantic retrieval
* BGE query prefix
* RRF ranking
* Empty results
* No evidence available
* Source citations
* Pending content exclusion
* Rejected content exclusion

### API and UX contracts

Test:

* Consistent error envelope
* No raw exception leakage
* Actionable user messages
* Correct HTTP semantics
* Upload guidelines displayed
* Processing status displayed
* Retry affordance
* Empty states
* Review decision feedback

---

## 18.2 Test layers

Use:

* Unit tests for deterministic domain logic.
* Integration tests for PostgreSQL, pgvector, migrations, and important provider boundaries.
* API tests for request/response contracts.
* A small number of Playwright end-to-end tests for critical workflows.

Do not force a fixed percentage split.

Use the smallest test type that provides meaningful confidence.

---

## 18.3 External systems

Mock external systems in most tests:

* Gemini
* Google Search Grounding
* Remote web pages
* Email provider, if added

Keep a small number of optional integration tests for real external providers. They must not be required for the normal test suite unless credentials are explicitly configured.

Do not over-mock your own business logic.

---

## 18.4 Regression tests

Every meaningful bug discovered during development should produce a regression test before or alongside the fix.

---

## 18.5 Test naming

Test names should communicate behavior.

Examples:

```python
test_empty_document_is_rejected_before_embedding()
test_duplicate_upload_does_not_create_second_job()
test_low_confidence_claim_requires_admin_review()
test_pending_knowledge_is_excluded_from_search()
test_grounding_timeout_preserves_submission_for_retry()
```

---

## 18.6 Coverage

Coverage is a diagnostic signal, not a target.

Do not add trivial tests solely to increase the percentage.

---

# 19. Docker and Deployment Rules

## 19.1 Docker is part of the product

The backend must be containerized.

The same Dockerfile should support local validation and production deployment where practical.

Use Docker Compose locally for:

* Backend
* PostgreSQL with pgvector
* Redis, if ARQ is used

The frontend may run with Vite locally and deploy separately to Vercel.

---

## 19.2 Deterministic model availability

Pre-download the BGE embedding model during the Docker build.

Do not download model weights during the first user request.

Configure Hugging Face cache paths explicitly.

Pin dependencies through the selected Python and JavaScript package-management files.

---

## 19.3 Docling resources

Docling is the heaviest dependency.

Assume at least 2 GB RAM for deployment and prefer 4 GB for reliable processing.

Do not configure unbounded concurrency.

Limit simultaneous document-processing jobs based on available memory.

A document-processing failure must not crash the API process.

---

## 19.4 Migrations

Run Alembic migrations as an explicit deployment step.

Do not silently create production schemas from ORM metadata.

---

## 19.5 Health checks

Provide:

* Liveness endpoint
* Readiness endpoint

Readiness should verify required infrastructure without performing expensive model inference.

---

## 19.6 Local setup

The repository should provide a straightforward setup flow.

Target:

```bash
cp .env.example .env
docker compose up --build
```

If the frontend requires a separate command, document it clearly.

Do not require reviewers to install PostgreSQL, Redis, pgvector, Docling system dependencies, or embedding models manually.

---

# 20. Documentation Rules

Maintain only documentation that reduces reviewer uncertainty.

Required:

* `README.md`
* `decisions.md`
* `AGENTS.md`
* `.env.example`

Do not create many overlapping architecture and design files unless there is a clear need.

`README.md` should explain:

* What the product does
* Who it is for
* Demo link
* Core user flow
* Architecture summary
* Supported constraints
* Setup
* Testing
* Deployment
* Screenshots or demo media

`decisions.md` should explain:

* The decision
* Alternatives considered
* Reasoning
* Trade-offs
* What was deliberately cut

Update `decisions.md` when a meaningful implementation decision changes.

---

# 21. Source-Control and Change Discipline

For each task:

1. Read the relevant existing files.
2. State the acceptance criteria.
3. Identify the smallest complete change.
4. List expected files to modify.
5. Implement only the requested scope.
6. Add meaningful tests.
7. Run formatting, linting, type checks, and relevant tests.
8. Review the diff for accidental scope expansion.
9. Remove generated noise.
10. Report what changed, commands run, results, and unresolved risks.

Do not modify unrelated files.

Do not reformat the entire repository for a small change.

Keep commits focused and reviewable.

---

# 22. Definition of Done

A task is complete only when all applicable conditions are met:

* Acceptance criteria are satisfied.
* The implementation follows `decisions.md` and `AGENTS.md`.
* Business behavior is covered by meaningful tests.
* Failure paths are handled.
* User-facing errors are plain-language and actionable.
* Internal errors are logged with sufficient context.
* Formatting passes.
* Linting passes.
* Type checking passes.
* Relevant tests pass.
* Database migrations are included when required.
* No secrets are committed.
* No dead code remains.
* No commented-out code remains.
* No placeholder TODOs remain unless explicitly documented.
* No unnecessary abstractions were introduced.
* No unrelated files were changed.
* Documentation is updated when behavior or setup changes.
* The diff has been manually reviewed.
* Remaining limitations and risks are reported honestly.

Never claim completion when verification has not passed.

---

# 23. Explicit Non-Goals

Do not add these unless the product scope is deliberately changed:

* Multiple knowledge domains
* Multi-language content
* Audio transcription
* Video ingestion
* YouTube ingestion
* Git repository ingestion
* Spreadsheet ingestion
* Presentation ingestion
* Entire-site crawling
* Private workspace connectors
* Real-time collaborative editing
* Comments
* Voting
* Reputation systems
* Personalized learning paths
* Course generation
* Knowledge graph visualization
* Enterprise RBAC
* Multi-tenant organizations
* Kubernetes
* Microservices
* Multiple vector databases
* Custom OCR engines
* Fine-tuned LLMs
* Custom embedding training
* Autonomous agents controlling workflows
* Automatic edits without user approval

---

# 24. Final Review Checklist for AI-Generated Changes

Before presenting any work as complete, explicitly check:

## Scope

* Did the change solve only the requested problem?
* Did it introduce speculative functionality?
* Did it conflict with the five-day scope?

## Architecture

* Was an existing library used where appropriate?
* Is custom code concentrated on product differentiation?
* Is the dependency direction clear?
* Is the implementation simpler than the alternatives?

## AI Usage

* Is the LLM used only where semantic intelligence is required?
* Does deterministic code own orchestration?
* Is the LLM output schema-validated?
* Are AI findings evidence-backed and explainable?

## Backend

* Are routes thin?
* Are state transitions explicit?
* Are transactions used where needed?
* Are domain errors meaningful?
* Are configuration values centralized?

## Frontend

* Are all UI states handled?
* Are upload constraints visible before submission?
* Are errors understandable and actionable?
* Is motion purposeful?
* Is the interface accessible?
* Is the design minimal without feeling generic?

## Testing

* Do tests protect real behavior?
* Are realistic edge cases covered?
* Are tests independent?
* Was framework behavior unnecessarily retested?
* Would the tests catch a production regression?

## Code Quality

* Are names clear?
* Are comments necessary?
* Does any comment merely restate code?
* Is there dead code?
* Is there unnecessary abstraction?
* Does the code look curated rather than generated?

## Operations

* Is the workflow observable?
* Are retries bounded?
* Are timeouts configured?
* Are secrets protected?
* Will the code run reliably in Docker?
* Are deployment resource constraints respected?

---

# Final Principle

> Use existing libraries for solved problems. Use deterministic software for orchestration and policy. Use LLMs only for intelligence that ordinary code cannot provide. Keep the architecture simple, the behavior explicit, the failures graceful, and the Knowledge Quality Engine at the center of the project.

```
```
