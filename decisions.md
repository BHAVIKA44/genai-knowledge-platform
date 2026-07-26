
# Engineering Decisions

## About This Document

This file records the meaningful product and engineering decisions made while building this project.

It is not a changelog and does not attempt to explain every implementation detail. It focuses on the decisions that shaped the product:

- what I chose
- what alternatives I considered
- why I made the decision
- which trade-offs I accepted
- what I deliberately left out

This document will continue to evolve as implementation exposes new constraints and changes some of the assumptions made during planning.

---

# 1. Problem Interpretation

## Decision

Build a collaborative Generative AI learning platform that converts messy learning resources into structured, validated, and queryable knowledge.

Users can contribute research papers, technical documentation, notes, public URLs, and readable screenshots. Before any contribution becomes searchable, it passes through a **Knowledge Quality Engine**.

## Alternatives Considered

- Generic document parser
- Chat-with-PDF application
- Invoice extraction system
- Contract intelligence platform
- General-purpose knowledge management platform
- Domain-agnostic RAG system

## Reasoning

The given problem statement was:

> Turn messy documents into structured, queryable data.

A basic implementation could parse documents, split them into chunks, generate embeddings, and provide a chat interface. Most of that workflow is already well supported by existing libraries.

The more difficult problem is deciding whether extracted information is trustworthy enough to enter a shared knowledge base.

This project therefore interprets the assignment as two connected problems:

1. Convert heterogeneous GenAI learning resources into a common structured format.
2. Prevent incomplete, duplicated, contradictory, outdated, or poorly extracted information from silently entering the knowledge base.

The query experience demonstrates the value of the structured data, but the primary engineering investment is the quality gate before publication.

## Trade-offs Accepted

Restricting the product to GenAI reduces its immediate applicability to other domains. In return, it allows more meaningful validation and a much more focused implementation.

## Deliberately Left Out

- Generic support for every knowledge domain
- General-purpose document management
- A standalone OCR or parsing engine
- Another basic chat-with-documents product

---

# 2. Product Scope

## Decision

Restrict the first version to English-language Generative AI learning resources.

Supported topics include:

- Large Language Models
- Transformers
- Embeddings
- Retrieval-Augmented Generation
- Vector databases
- Agents
- Model Context Protocol
- Prompt engineering
- Fine-tuning
- Evaluation
- Inference
- AI frameworks and tooling
- Relevant research papers and technical documentation

## Alternatives Considered

- Support all technical topics
- Support arbitrary uploaded documents
- Support multiple specialist domains such as legal, healthcare, and finance

## Reasoning

The Knowledge Quality Engine requires context about the domain it is validating. A system that claims to validate every possible subject would either provide shallow checks or make claims it cannot defend.

Restricting the domain provides:

- clearer product positioning
- more representative test data
- stronger prompts and validation criteria
- simpler demonstration scenarios
- a realistic five-day scope

## Trade-offs Accepted

Some technically valid documents will be rejected because they are not related to Generative AI.

## Deliberately Left Out

- Healthcare knowledge
- Legal knowledge
- Financial advice
- General educational documents
- Multilingual content

---

# 3. Supported Inputs and Product Constraints

## Decision

Support only the input formats commonly used by GenAI learners and reliably handled by the selected ingestion stack.

### Supported Inputs

- PDF
- Markdown
- Plain text
- DOCX, if its support remains stable during implementation
- PNG
- JPEG
- Public technical documentation and blog URLs

### Intended Limits

- Maximum file size: 50 MB
- Maximum document length: 250 pages
- Maximum individual image size: 10 MB
- English-language content only
- Public URLs only
- Maximum concurrent uploads per user: 5
- Minimum extracted content: 50 meaningful characters

These limits may be adjusted after deployment testing, but any change will be documented.

## Alternatives Considered

- Supporting every format handled by Docling
- Unlimited file sizes
- Entire website crawling
- ZIP and folder ingestion
- Audio, video, and YouTube transcription
- Git repository ingestion

## Reasoning

Supporting many formats would increase test surface, failure modes, deployment requirements, and UI complexity without strengthening the Knowledge Quality Engine.

The product contract should be clear before upload. Constraints will be visible near the upload interface and in an upload-guidelines dialog.

Unsupported scenarios will be handled as deliberate product boundaries rather than accidental failures.

## User Experience for Unsupported Inputs

Users should receive simple and actionable messages.

For example:

> This file type is not supported yet. Please upload a PDF, Markdown file, text file, DOCX file, or a clear PNG/JPEG image.

Instead of:

> Unsupported MIME type.

## Deliberately Left Out

- PPTX
- XLSX
- CSV
- ZIP
- Audio
- Video
- YouTube
- Git repositories
- Entire-site crawling
- Private Google Docs
- Private Notion pages
- Authentication-protected websites
- Heavily handwritten notes

---

# 4. Knowledge Validation Before Publication

## Decision

Every contribution must pass through the Knowledge Quality Engine before it becomes searchable.

Successfully parsing a document does not imply that its content should be trusted or published.

## Alternatives Considered

- Publish immediately after parsing
- Validate only when users query the content
- Allow all uploads and depend on community reporting
- Require manual approval for every document

## Reasoning

Most RAG systems treat ingested documents as trusted ground truth. If poor information enters the retrieval corpus, future answers become unreliable regardless of retrieval quality.

Validation at ingestion time prevents the same issue from affecting every future query.

The engine will evaluate areas such as:

- extraction quality
- metadata completeness
- domain relevance
- exact duplicates
- near duplicates
- contradictory knowledge
- missing evidence
- potentially outdated technical claims
- claims requiring external verification

## Trade-offs Accepted

Ingestion will take longer because documents must be evaluated before publication.

This is acceptable because the product prioritizes knowledge quality over immediate indexing.

## Deliberately Left Out

The platform will not claim that it guarantees objective truth. It improves knowledge quality using evidence, confidence, consistency checks, and human review.

---

# 5. LLMs Provide Intelligence, Not Orchestration

## Decision

Use the LLM only for tasks that genuinely require semantic understanding or judgment.

Deterministic application code owns workflows, rules, state transitions, retries, persistence, and publication decisions.

## LLM Responsibilities

- structured knowledge extraction
- topic and entity extraction
- claim identification
- semantic contradiction analysis
- freshness analysis
- suggested corrections
- concise explanations
- external evidence evaluation

## Application Responsibilities

- MIME validation
- upload limits
- SHA-256 hashing
- URL normalization
- duplicate job prevention
- timeout and retry policies
- state transitions
- confidence thresholds
- publication routing
- database writes
- approved-only search filtering

## Alternatives Considered

- Agent-driven workflow orchestration
- LangGraph controlling the complete pipeline
- LLM-generated decisions directly updating the database
- Allowing the model to decide retry and publication behavior

## Reasoning

LLMs are probabilistic. Workflow state and publication rules need predictable, testable behavior.

The model should return structured evidence and findings. The application should decide what happens next.

This separation improves:

- testability
- debuggability
- safety
- observability
- provider portability

## Deliberately Left Out

- Autonomous agents controlling the workflow
- LLM-generated database queries
- Model-controlled retries
- Direct publishing based solely on model prose

---

# 6. Knowledge Quality Engine Design

## Decision

Build the Knowledge Quality Engine as a composition of focused validators rather than one large prompt or a complex rule framework.

Possible validators include:

- `ExtractionQualityValidator`
- `MetadataValidator`
- `DomainRelevanceValidator`
- `ExactDuplicateValidator`
- `SemanticDuplicateValidator`
- `ContradictionValidator`
- `CitationValidator`
- `FreshnessValidator`
- `ExternalEvidenceValidator`

Each validator returns structured findings.

## Finding Structure

A finding should contain information such as:

- stable issue code
- category
- severity
- confidence
- user-facing title
- explanation
- evidence
- suggested action
- suggested correction
- whether external verification is required

## Alternatives Considered

- One large LLM prompt returning a final score
- Generic rules engine
- Plugin framework
- Deep validator inheritance hierarchy
- Hard-coded validation logic inside API routes

## Reasoning

Focused validators are independently testable and easier to evolve.

Composition provides sufficient extensibility without creating an unnecessary plugin framework. New validators can be added without rewriting unrelated checks.

## Trade-offs Accepted

Some orchestration code is required to combine findings and produce a final route.

## Deliberately Left Out

- General-purpose rule DSL
- Runtime plugin loading
- User-configurable validation pipelines
- Complex inheritance trees

---

# 7. Quality Score and Review Routing

## Decision

Produce a Knowledge Quality Score as an operational signal, while preserving the individual findings that contributed to it.

The score must not be presented as an objective probability that the content is true.

## Intended Workflow

- No blocking issues and high confidence → auto-publish
- Clear, high-confidence correction → contributor review
- Ambiguous, conflicting, or weakly supported finding → admin review
- Unsupported, empty, unreadable, or invalid input → reject before publication

Exact thresholds will be centralized in configuration and finalized after testing with representative documents.

## Alternatives Considered

- Binary pass/fail
- Manual review for every submission
- Automatic publication for every successful model response
- A score without detailed findings

## Reasoning

Real knowledge validation is not binary.

High-confidence cases should not create unnecessary human work, while uncertain cases should not be silently accepted.

The score supports routing, but explanations and evidence remain more important than the number itself.

## Deliberately Left Out

- Pretending the score is mathematically precise
- Silent automatic corrections
- Multi-level enterprise approval workflows
- Reviewer voting

---

# 8. User Approval for Suggested Corrections

## Decision

The system may suggest corrections but must never silently rewrite contributor content.

## Alternatives Considered

- Automatically replace incorrect text
- Publish an AI-rewritten version
- Store only the corrected version
- Allow the model to overwrite the original submission

## Reasoning

Contributors remain the owners of their content.

Every correction should show:

- original claim
- detected issue
- suggested correction
- confidence
- supporting evidence

The contributor can accept or decline the correction. Documents with unresolved blocking issues will not become searchable.

## Trade-offs Accepted

The workflow requires an additional user interaction for some submissions.

## Deliberately Left Out

- Automatic rewriting without consent
- Destructive edits to the original upload
- Hidden AI modifications

---

# 9. Human Review for Uncertain Cases

## Decision

Route unresolved or low-confidence cases to an in-application admin review queue.

## Alternatives Considered

- Email-only approval
- Reject all uncertain content
- Automatically publish uncertain content
- Build a complex moderation system

## Reasoning

Email introduces additional infrastructure and makes the review experience difficult to demonstrate.

A small in-app review workflow is easier to use, test, and explain.

The reviewer should see:

- original source
- extracted knowledge
- findings
- external evidence
- suggested correction
- approve, reject, or request-edit actions

## Deliberately Left Out

- Reviewer assignment
- Multi-stage approvals
- SLA management
- Voting
- Comments and discussion threads
- Email notifications in the initial version

---

# 10. Docling for Document Ingestion

## Decision

Use Docling for document parsing, layout understanding, reading order, table handling, and OCR integration.

## Alternatives Considered

- Unstructured
- Apache Tika
- PyMuPDF
- LangChain document loaders
- Separate custom parsers for every format
- Managed document extraction APIs

## Reasoning

Document parsing is not the differentiator of this project.

Docling provides a unified representation across the selected file types and reduces the amount of custom ingestion code.

This allows the implementation to focus on the Knowledge Quality Engine.

## Trade-offs Accepted

Docling has a larger runtime and memory footprint than lightweight text-only parsers.

Deployment must therefore provide enough memory, and processing concurrency must remain bounded.

## Graceful Failure

If extraction produces insufficient or unreliable text, the application should not continue into embeddings and validation.

The user should see:

> We could not reliably read this document. Please upload a clearer image or the original digital copy.

## Deliberately Left Out

- Custom OCR engine
- OCR model training
- Guaranteed handwriting recognition
- Attempting to infer text from unreadable content

---

# 11. Deterministic Ingestion Validation

## Decision

Perform inexpensive deterministic checks before Docling, embeddings, or LLM calls.

## Checks

- allowed file extension
- MIME validation
- basic stream/header verification
- file size
- page count where available
- zero-byte files
- whitespace-only content
- minimum extracted character count
- exact file duplicate using SHA-256
- duplicate normalized URL
- existing active processing job
- safe filename generation

## URL Safety

URL ingestion should:

- permit only HTTP and HTTPS
- use a strict timeout
- follow at most two redirects
- reject authentication pages
- reject paywalls and anti-bot challenges
- handle 403, 404, 429, and server failures
- block private and local network addresses to reduce SSRF risk
- never attempt to bypass access restrictions

## Alternatives Considered

- Pass all uploads directly to Docling
- Trust the file extension
- Handle invalid inputs after expensive processing

## Reasoning

Invalid inputs should be rejected as early and cheaply as possible.

This reduces:

- unnecessary model usage
- duplicate jobs
- deployment load
- confusing processing failures
- security risk

## Deliberately Left Out

- Full malware scanning
- Enterprise content security scanning
- Bypassing robots or authentication controls

---

# 12. Gemini 2.5 Flash as the Primary Reasoning Model

## Decision

Use Gemini 2.5 Flash as the main reasoning model for structured extraction and evidence-backed validation.

The exact model identifier and SDK version will be pinned and revalidated during implementation.

## Alternatives Considered

- Claude Sonnet
- OpenAI reasoning models
- Open-weight local models
- Separate LLM and search providers
- Gemini's larger models

## Reasoning

The system needs:

- reliable structured output
- long-context support
- low latency
- native Google Search Grounding
- a practical free or low-cost tier
- simple deployment without hosting an LLM

Native search grounding eliminates a separate search provider and retrieval orchestration layer.

The decision optimizes the complete architecture rather than selecting a model based only on benchmark quality.

## Trade-offs Accepted

- Search grounding can return imperfect or weak sources.
- Gemini may be weaker than larger models for some complex reasoning tasks.
- API behavior and quotas may evolve.
- The application depends on a hosted provider.

These risks are mitigated through:

- structured output validation
- bounded retries
- evidence inspection
- human review
- provider isolation behind a small client boundary
- pinned dependencies

## Deliberately Left Out

- Hosting a local LLM
- Using the LLM as the workflow engine
- Building custom web-search infrastructure
- Selecting the most expensive model for every request

---

# 13. Selective Google Search Grounding

## Decision

Use Google Search Grounding only when the Knowledge Quality Engine identifies a claim that materially requires current external evidence.

## Appropriate Cases

- model or framework ownership
- current API behavior
- release-specific capabilities
- deprecations
- rapidly changing GenAI claims
- content that conflicts with approved knowledge
- potentially outdated technical guidance

## Cases That Do Not Need Grounding

- file validation
- missing title
- empty content
- exact duplicate detection
- MIME validation
- extraction quality
- required metadata

## Alternatives Considered

- Ground every extracted claim
- Never use the web
- Add Tavily, SerpAPI, or another search provider
- Build custom crawling and ranking

## Reasoning

Searching for every claim would increase latency, consume quota, and add noise.

Selective grounding treats web search as a confidence-recovery mechanism rather than a default step.

## Trade-offs Accepted

Some claims may remain unverified if the engine does not route them to grounding. Representative testing and conservative review routing will be used to reduce this risk.

## Deliberately Left Out

- Full internet fact-checking
- Crawling arbitrary numbers of sources
- Treating a single search result as absolute truth

---

# 14. FastAPI and Pydantic for the Backend

## Decision

Use Python 3.12, FastAPI, Pydantic v2, and `pydantic-settings`.

## Alternatives Considered

- Django
- Flask
- Spring Boot
- NestJS
- Express

## Reasoning

Python provides the strongest integration with Docling, Sentence Transformers, and the selected AI tooling.

FastAPI provides:

- typed request and response models
- dependency injection
- OpenAPI documentation
- asynchronous API support
- low framework boilerplate

Pydantic will validate:

- API input
- API output
- configuration
- internal domain boundaries
- every LLM response

## Deliberately Left Out

- A larger framework with unused functionality
- Untyped dictionaries as API contracts
- Parsing model prose manually

---

# 15. SQLModel with an Escape Hatch to SQLAlchemy

## Decision

Use SQLModel for the initial data model while retaining the option to use plain SQLAlchemy 2.0 for advanced mappings or queries.

## Alternatives Considered

- Raw SQLAlchemy models and separate Pydantic schemas from the start
- Django ORM
- Prisma
- Raw SQL for all persistence

## Reasoning

SQLModel reduces boilerplate and aligns naturally with FastAPI and Pydantic.

The project's initial relational model is not expected to require advanced ORM inheritance or highly complex relationships.

If SQLModel becomes restrictive, the project can introduce explicit SQLAlchemy models in the affected area rather than prematurely increasing boilerplate everywhere.

## Trade-offs Accepted

SQLModel may lag behind some advanced SQLAlchemy or Pydantic features.

## Deliberately Left Out

- Generic repository framework
- Base CRUD services
- Hiding every ORM operation behind unnecessary abstractions

---

# 16. PostgreSQL as the Single System of Record

## Decision

Use PostgreSQL for relational data, document metadata, review state, structured knowledge, full-text search, and embeddings.

## Alternatives Considered

- MongoDB
- Firebase
- PostgreSQL plus a dedicated vector database
- Multiple specialized databases

## Reasoning

The product contains strongly related entities:

- users or contributors
- documents
- processing jobs
- extracted knowledge
- validation findings
- reviews
- chunks
- embeddings

PostgreSQL provides:

- transactions
- relational integrity
- constraints
- JSONB where flexibility is useful
- Full-Text Search
- pgvector support

A single datastore reduces deployment, synchronization, backup, and consistency complexity.

## Deliberately Left Out

- MongoDB
- Elasticsearch
- Pinecone
- Weaviate
- Qdrant
- Multi-database synchronization

---

# 17. BGE Small for Local Embeddings

## Decision

Use `BAAI/bge-small-en-v1.5` through Sentence Transformers for local English embeddings.

## Alternatives Considered

- Hosted OpenAI embeddings
- Hosted Gemini embeddings
- `all-MiniLM`
- E5 models
- BGE base or large
- Nomic embeddings

## Reasoning

The selected model provides a good balance of:

- retrieval quality
- CPU performance
- model size
- zero per-request cost
- simple local deployment

Keeping embeddings local avoids rate limits and separates retrieval from the reasoning provider.

## Query Formatting

BGE uses asymmetric retrieval formatting.

- Document chunks are embedded directly.
- Search queries are prefixed with:

> Represent this sentence for searching relevant passages:

This behavior will be centralized in the embedding service.

## Deployment

The model will be downloaded during the Docker build rather than on the first user request.

## Trade-offs Accepted

A larger model could improve retrieval quality, but would increase memory use, image size, and latency.

## Deliberately Left Out

- Custom embedding training
- Fine-tuning
- Paying for hosted embeddings
- Runtime model downloads

---

# 18. pgvector with HNSW

## Decision

Store 384-dimensional BGE embeddings in PostgreSQL using pgvector and index them with HNSW using cosine distance.

## Alternatives Considered

- Exact brute-force vector search
- IVFFlat
- Dedicated vector database
- No vector index

## Reasoning

Exact search would be sufficient for the initial demonstration dataset, but HNSW provides a simple growth path without adding another service.

pgvector integrates directly with:

- metadata filters
- document status
- contributor information
- review state
- full-text ranking

## Trade-offs Accepted

Approximate search may not return the mathematically exact nearest neighbors in every case. For the expected product scale, the latency and operational benefits are acceptable.

## Deliberately Left Out

- Tuning ANN parameters without measurements
- Scaling for billions of embeddings
- Distributed vector infrastructure

---

# 19. Hybrid Search with Reciprocal Rank Fusion

## Decision

Combine PostgreSQL Full-Text Search with pgvector semantic retrieval and merge the rankings using Reciprocal Rank Fusion.

## Alternatives Considered

- Semantic search only
- Keyword search only
- Directly adding lexical and vector scores
- External search engine
- Reranking model

## Reasoning

Semantic retrieval is useful for conceptual questions, but exact names and technical identifiers are often better served by lexical search.

For example:

- “Explain tool calling” benefits from semantic retrieval.
- “Find documents mentioning `gpt-4.1`” benefits from exact lexical matching.

The two scoring systems operate on different scales. RRF combines ranked positions rather than attempting to calibrate incompatible raw scores.

## Trade-offs Accepted

The retrieval implementation becomes slightly more complex than pure vector search.

## Deliberately Left Out

- Elasticsearch
- OpenSearch
- Dedicated reranking model
- Multi-stage retrieval pipelines
- Query expansion agents

---

# 20. Retrieval and Reasoning as Separate Systems

## Decision

Use BGE and PostgreSQL for retrieval, then Gemini for synthesis and answer generation.

## Alternatives Considered

- Let Gemini perform both retrieval and reasoning
- Use one hosted provider for embeddings and generation
- Pass complete documents to the LLM without retrieval

## Reasoning

Retrieval and reasoning are different workloads.

Separating them provides:

- lower cost
- predictable retrieval
- provider independence
- easier testing
- easier future replacement
- reduced context usage

## Deliberately Left Out

- Sending the entire knowledge base to the model
- Tight coupling between retrieval and one model provider
- LLM-generated search queries without deterministic controls

---

# 21. Source-Backed Answers Only

## Decision

Generate answers only from approved knowledge and always include supporting source references.

## Alternatives Considered

- Let Gemini answer from its own memory
- Show uncited generated responses
- Search pending and rejected documents
- Return only raw chunks without synthesis

## Reasoning

The purpose of the product is to expose trusted shared knowledge, not provide a general chatbot.

Search and answer generation must exclude:

- pending documents
- rejected documents
- failed documents
- unapproved corrections
- contributor drafts

If sufficient supporting evidence does not exist, the system should say so rather than fabricate an answer.

## Deliberately Left Out

- Unrestricted general-purpose chat
- Answers based only on the model's memory
- Hidden sources
- Search over unapproved knowledge

---

# 22. Background Processing

## Decision

Process document ingestion asynchronously because parsing, OCR, grounding, embeddings, and validation can exceed normal HTTP request durations.

Use a small job abstraction. ARQ and Redis are the intended implementation if durable processing is needed.

## Alternatives Considered

- Synchronous request processing
- FastAPI `BackgroundTasks`
- Celery
- RabbitMQ
- Kafka
- Temporal

## Reasoning

The user should receive confirmation quickly and then see the document progress through real processing stages.

ARQ is lighter than Celery and fits the Python asynchronous stack.

The first vertical slice may begin with a replaceable background boundary, but the deployed workflow should not pretend that in-process background tasks provide durable queue semantics.

## Trade-offs Accepted

Redis adds another deployed component.

If implementation time or deployment reliability becomes an issue, this decision may be revisited and documented.

## Deliberately Left Out

- Distributed workflow orchestration
- Kafka
- Temporal
- Unbounded concurrency
- Fake progress indicators

---

# 23. Explicit Processing States

## Decision

Represent the document lifecycle using one explicit state field and validated transitions.

Possible states include:

- uploaded
- queued
- parsing
- extracting
- validating
- contributor review required
- admin review required
- approved
- rejected
- failed

## Alternatives Considered

- Multiple booleans such as `is_processing`, `needs_review`, and `is_approved`
- Let background jobs update fields independently
- Infer state from missing values

## Reasoning

Multiple flags can produce impossible combinations.

A single state machine makes behavior easier to reason about, test, display, and debug.

## Deliberately Left Out

- A general workflow engine
- Dynamically configurable state machines
- Event sourcing

---

# 24. Graceful Failure as Product Behavior

## Decision

Translate all known technical failures into clear, actionable, non-technical messages.

## Examples

Instead of:

> OCR confidence below threshold.

Show:

> We could not reliably read this document. Please upload a clearer scan or the original digital file.

Instead of:

> Gemini returned invalid JSON.

Show:

> We could not finish validating this resource right now. Please try again shortly.

Instead of:

> pgvector insertion failed.

Show:

> We could not finish adding this resource to the knowledge base. Your upload has not been published.

## Alternatives Considered

- Surface raw provider errors
- Use one generic “Something went wrong” message
- Return technical stack traces in development-style UI

## Reasoning

Users need to understand what happened and what they can do next. They do not need to know which library or service failed.

Detailed diagnostics belong in structured logs.

## Deliberately Left Out

- Exposing provider names in normal user errors
- Raw status codes without explanation
- Silent failures

---

# 25. AI-Native but Minimal Frontend

## Decision

Build a modern, technical, AI-native interface with strong typography, generous whitespace, purposeful motion, and progressive disclosure.

The visual direction may take inspiration from products such as Zamp, Linear, Vercel, OpenAI, Anthropic, and Arc without copying their branding or layouts.

## Alternatives Considered

- Traditional enterprise admin dashboard
- Highly decorative AI interface
- Card-heavy analytics dashboard
- Plain CRUD application

## Reasoning

The interface should make a complex validation workflow feel calm and understandable.

The product should emphasize:

- upload guidance
- real processing progress
- validation explanations
- evidence
- review decisions
- source-backed search

The UI should feel distinctive without competing with the product.

## Deliberately Left Out

- Dense dashboards
- Decorative 3D graphics
- Constant glowing effects
- Excessive animation
- A custom design system
- Copying another company's visual identity

---

# 26. Frontend Library-First Approach

## Decision

Use mature frontend libraries for solved interaction and state-management problems.

## Selected Tools

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
- Framer Motion, used selectively
- React Markdown
- A PDF viewer only where source inspection requires it

## Alternatives Considered

- Building a custom component library
- Redux for all state
- Custom drag-and-drop
- Custom form handling
- Custom toast system
- Handwritten modal and accessibility primitives

## Reasoning

Frontend engineering effort should go toward the product journey rather than rebuilding buttons, dialogs, tables, uploads, and server-state caching.

## Deliberately Left Out

- Custom design-system package
- Global state management without a demonstrated need
- Animation-heavy UI framework
- Unnecessary component abstraction

---

# 27. Progressive Disclosure

## Decision

Show the most important result first and reveal complexity only when the user requests it.

## Examples

- Show the publication status before individual validator details.
- Show a concise issue summary before complete evidence.
- Open full source passages in a drawer or dedicated source view.
- Keep model and processing metadata out of the primary experience.
- Show upload constraints concisely, with complete guidance available on demand.

## Alternatives Considered

- Display every finding and metadata field on one screen
- Create many separate pages
- Hide all details behind an opaque score

## Reasoning

The system performs complex work. The interface should not force users to understand all of it at once.

## Deliberately Left Out

- Expert-level controls in the default interface
- Displaying internal chunks
- Raw model output

---

# 28. Purposeful Motion and Small Moments of Delight

## Decision

Use motion to communicate state and include a few restrained moments of delight.

## Appropriate Uses

- transition from upload to processing
- show actual processing stages
- reveal findings smoothly
- highlight source evidence
- acknowledge the first approved contribution
- display a small knowledge-status indicator during long-running work

## Alternatives Considered

- No motion
- Continuous animation
- Full mascot system
- Gamification

## Reasoning

Long-running AI workflows benefit from visual feedback. Small moments of personality can make the product memorable, provided they remain rare and non-blocking.

## Deliberately Left Out

- Animating every component
- Confetti after every action
- A distracting character
- Motion that delays interaction
- Fake progress

---

# 29. Meaningful Testing Over Coverage Targets

## Decision

Test business behavior, critical workflows, contracts, and realistic failure modes rather than optimizing for a coverage percentage.

## Highest-Priority Areas

### Knowledge Quality Engine

- exact duplicates
- near duplicates
- missing metadata
- contradiction findings
- citation findings
- freshness findings
- score calculation
- review routing
- malformed model output
- conflicting external evidence

### Ingestion

- empty files
- whitespace-only files
- unsupported extensions
- MIME mismatch
- binary renamed as text
- oversized documents
- duplicate active jobs
- duplicate completed uploads
- corrupted PDFs
- unreadable images
- unsupported language
- non-GenAI content
- URL timeout and redirects
- private-network URLs

### Workflow

- allowed state transitions
- invalid state transitions
- idempotent review actions
- transaction rollback
- bounded retries

### Retrieval

- approved-only search
- exact keyword retrieval
- semantic retrieval
- BGE query instruction
- RRF ranking
- no-evidence behavior
- source citations

## Alternatives Considered

- Target a high percentage such as 90%
- Test every private helper
- Snapshot-test most UI components
- Mock every dependency

## Reasoning

A lower coverage number concentrated on important behavior is more valuable than high coverage created by trivial tests.

## Deliberately Left Out

- Testing framework internals
- Tests written only to raise the percentage
- Exhaustive visual snapshots
- Real external API calls in the normal test suite

---

# 30. Feature-Oriented Code Organization

## Decision

Organize the codebase around product capabilities rather than large global folders such as controllers, services, and repositories.

Expected backend capabilities include:

- documents
- knowledge quality
- reviews
- search
- LLM integration
- workers
- shared core infrastructure

Expected frontend features include:

- upload
- processing
- knowledge exploration
- search
- review

## Alternatives Considered

- Global `controllers/`, `services/`, `repositories/`, and `models/`
- Highly layered clean-architecture template
- One large services module

## Reasoning

Feature ownership keeps related code together and makes changes easier to locate.

The structure should emerge as functionality is implemented. Empty folders should not be created for hypothetical needs.

## Deliberately Left Out

- Generic `helpers`
- `misc`
- `manager`
- universal `BaseService`
- generic repositories
- deep folder nesting without real complexity

---

# 31. Code Should Feel Curated, Not Generated

## Decision

Treat AI-generated code as a first draft that must be reviewed and simplified before it is committed.

## Required Cleanup

- remove comments that restate the code
- remove tutorial-style explanations
- remove dead branches and unused helpers
- replace vague names
- remove speculative abstractions
- remove placeholder TODOs
- follow conventions already present in the repository
- review the complete diff manually

## Commenting Standard

Comments should explain:

- why a non-obvious decision exists
- a business constraint
- a security requirement
- a library limitation
- an accepted trade-off

Comments should not narrate obvious code.

## Alternatives Considered

- Commit generated code as-is
- Add comments to every function
- Build abstractions preemptively to appear sophisticated

## Reasoning

Top-quality code feels intentional. Every file, dependency, abstraction, and comment should justify its existence.

## Deliberately Left Out

- Artificial complexity
- Over-commenting
- Decorative design patterns
- Unused future-proofing

---

# 32. Extensibility Without Over-Engineering

## Decision

Design for likely changes through clear boundaries and composition, not through speculative frameworks.

## Likely Extension Points

- new quality validators
- different LLM provider
- different embedding model
- new supported document source
- new review-routing rule
- different ranking strategy

## Alternatives Considered

- Interface for every class
- Abstract factory for each dependency
- Runtime plugin system
- Event bus
- Generic workflow engine

## Reasoning

Extensibility should mean that a component can be replaced or added without affecting unrelated modules.

It should not mean making today's code harder to understand for hypothetical future scenarios.

## Deliberately Left Out

- Abstractions with one implementation and no likely alternative
- General-purpose plugin architecture
- Premature event-driven design

---

# 33. Docker for Reproducible Setup and Deployment

## Decision

Containerize the backend and provide Docker Compose for local PostgreSQL, pgvector, and Redis where required.

## Alternatives Considered

- Manual local installation
- Platform-specific setup scripts
- Dockerizing every component, including frontend development
- Kubernetes

## Reasoning

The reviewer should not need to manually install:

- PostgreSQL
- pgvector
- Redis
- Docling system dependencies
- Python packages
- embedding model weights

The Docker image will pre-download the embedding model and provide a predictable environment for deployment.

The frontend may run through Vite locally and deploy separately to Vercel.

## Trade-offs Accepted

The backend image will be relatively large because of Docling and the local embedding model.

## Deliberately Left Out

- Kubernetes
- Helm
- Multi-container production orchestration beyond what is needed
- Runtime model downloads

---

# 34. Deployment Architecture

## Decision

Use a simple managed deployment:

- Vercel for the frontend
- container-based hosting for the FastAPI backend and worker
- managed PostgreSQL with pgvector
- managed Redis only if the durable queue is retained

The backend should have at least 2 GB RAM, with 4 GB preferred for more reliable Docling processing.

## Alternatives Considered

- Free 512 MB backend
- Self-managed VM
- Kubernetes cluster
- Serverless-only backend
- Hosting local LLMs

## Reasoning

Docling and local embeddings have meaningful memory requirements. Paying a small amount for predictable resources is preferable to an unreliable demo.

Managed services reduce operational work while keeping the application realistic and deployable.

## Deliberately Left Out

- Multi-region deployment
- Auto-scaling infrastructure
- GPU deployment
- Hosting an LLM
- Enterprise disaster recovery

---

# 35. Structured Logging and Observability

## Decision

Use structured logs with request, job, and document identifiers.

Track important business events and stage durations.

## Events

- upload accepted or rejected
- duplicate detected
- parsing started and completed
- extraction completed
- grounding invoked
- quality validation completed
- contributor review requested
- admin review requested
- knowledge approved or rejected
- indexing completed
- search completed

## Durations

- parsing
- OCR
- LLM extraction
- grounding
- embedding
- validation
- retrieval
- answer generation

## Alternatives Considered

- Print statements
- Free-form logs
- Add a full observability platform
- No timing information

## Reasoning

Long AI pipelines are difficult to debug without stage-level visibility.

Structured logs provide sufficient operational insight for the project without introducing a large observability stack.

## Deliberately Left Out

- Full distributed tracing platform
- Production analytics dashboard
- Logging full documents or secrets

---

# 36. Documentation Strategy

## Decision

Keep repository documentation focused:

- `README.md`
- `decisions.md`
- `AGENTS.md`
- `.env.example`

Do not distribute the same reasoning across many overlapping documents.

## Alternatives Considered

- Separate architecture, system design, API, testing, and deployment documents
- Minimal README only
- Large collection of project notes

## Reasoning

Zamp explicitly requested `decisions.md`, so it should contain the meaningful design reasoning and trade-offs.

The README should optimize for understanding and setup.

`AGENTS.md` should guide AI-assisted development.

This avoids documentation noise and respects reviewer time.

## Deliberately Left Out

- `ARCHITECTURE.md`
- `SYSTEM_DESIGN.md`
- `ROADMAP.md`
- `NOTES.md`
- `FUTURE_WORK.md`
- multiple files repeating the same information

---

# 37. Deliberately Excluded Product Features

The following capabilities are valuable, but were deliberately excluded because they would increase breadth without strengthening the core engineering problem:

- real-time collaborative editing
- comments
- reactions or voting
- reputation systems
- document version history
- organization workspaces
- enterprise RBAC
- multilingual content
- personalized learning paths
- course generation
- audio and video ingestion
- GitHub ingestion
- entire website crawling
- spreadsheets and presentations
- knowledge graph visualization
- fine-tuned language models
- custom embedding training
- multiple LLM providers in the first version
- multiple vector databases
- automatic corrections without approval
- distributed microservices
- Kubernetes
- multi-region deployment

These exclusions are not a claim that the features lack value. They reflect the decision to spend limited implementation time on the Knowledge Quality Engine, reliability, tests, deployment, and user experience.

---

# Closing Principle

The project is guided by one central engineering principle:

> Use existing libraries for solved problems. Use deterministic software for workflow and policy. Use LLMs only for intelligence that ordinary code cannot provide.

Document parsing, OCR, embeddings, UI components, migrations, background processing, and vector storage are delegated to mature tools.

Custom engineering effort is concentrated on the part that differentiates the product: determining whether extracted knowledge is reliable enough to become part of a shared, queryable knowledge base.

The objective is not to build the largest possible project in five days. It is to make a small number of important product and engineering decisions well, implement them cleanly, and build something that can be understood, tested, deployed, and trusted.

