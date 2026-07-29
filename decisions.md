# Decisions

## 1. Reframing the problem: from document ingestion to trusted knowledge

The brief was to turn messy documents into structured, queryable data. I chose not to make parsing the differentiator. Parsing matters: without reliable extraction there is no useful knowledge product. PDF layout, text extraction, OCR, chunking, and embeddings already have mature tools. Building another parser would have been incremental engineering in a five-day exercise.

The harder product question is what happens after text is extracted: **should this information become part of a shared knowledge base at all?** A polished retrieval experience can still be confidently wrong when its corpus contains irrelevant, duplicated, unreadable, or misleading material. Search quality therefore starts at admission, not ranking.

I framed the product as a trusted-knowledge workflow:

```text
ingestion → quality evaluation → review where needed → trusted indexing → queryable knowledge
```

Trust is the differentiator; parsing is the enabler. Success is not maximum upload throughput or the largest corpus. It is a small, inspectable set of Generative AI learning resources that users can search with confidence. I did not optimize for broad document coverage, unconstrained chat, or fully automated publication.

## 2. Product principles

**Quality before availability.** A successfully uploaded file is not automatically useful knowledge. Documents are evaluated before they can influence retrieval.

**Review before retrieval.** Only `APPROVED` documents are chunked, embedded, and considered by search. Pending, rejected, failed, and admin-review documents remain outside the retrieval corpus.

**Explicit states over hidden automation.** The document lifecycle is modeled as `UPLOADED`, `PROCESSING`, `VALIDATING`, `APPROVED`, `CONTRIBUTOR_REVIEW_REQUIRED`, `ADMIN_REVIEW_REQUIRED`, `REJECTED`, or `FAILED`. This prevents the UI and API from collapsing materially different outcomes into a vague “processed” state.

**Human judgment for material ambiguity.** The system can recognize obvious mechanical defects, but it should not quietly rewrite a contributor’s content or pretend semantic uncertainty is deterministic. It asks for an explicit contributor decision only for objective, high-confidence corrections; material concerns are held for admin review.

**Graceful degradation over false confidence.** External verification and model providers can be unavailable. An outage is not evidence that a document is wrong and must not leak provider internals. The platform uses available evidence or fails safely.

## 3. Scope: what I built and what I deliberately did not build

The implementation is a focused vertical slice for English-language Generative AI learning material. It supports digital PDFs, Markdown, and plain text; normalizes content; applies deterministic and semantic checks; persists document state; supports approval, rejection, contributor review, and admin review; indexes accepted content; and answers questions from reviewed knowledge.

I kept the input contract narrow. Images, scanned PDFs, DOCX, HTML, URLs, and pasted notes are not supported. Digital PDFs are parsed with OCR disabled, so a scan fails safely rather than producing unreliable text. The limits are a maximum file size of 10 MB, a maximum of 50 PDF pages, and at least 150 meaningful characters. A title is optional, and a Markdown heading can provide a fallback title.

I deferred a durable distributed queue, a full admin-review workspace, broad format support, authentication and multi-tenancy, learned ranking, and a model-only answer fallback. They are sensible production evolutions, but not prerequisites for validating the central thesis: a knowledge base should decide what it trusts before it retrieves.

## 4. Knowledge Quality Engine

The Knowledge Quality Engine is the admission boundary between raw source material and searchable knowledge. It returns typed findings and a recommended route.

The evaluation is layered. Cheap, deterministic checks run before parsing-intensive or provider-backed work: extension and MIME agreement, non-empty input, size, PDF page count, content length, English-language signal, GenAI relevance, professional-profile detection, and SHA-256 identity. This avoids spending provider calls and embedding work on files that are plainly outside scope or unusable.

The semantic stage produces structured topics, claims, and findings. The application then applies explicit routing boundaries:

| Outcome | Decision boundary |
| --- | --- |
| `APPROVED` | Readable, relevant material with no material blocker; optional suggestions do not stop publication. |
| `CONTRIBUTOR_REVIEW_REQUIRED` | One objective deterministic correction, currently an adjacent duplicated word, requires consent. |
| `ADMIN_REVIEW_REQUIRED` | A material semantic or factual concern needs human judgment. |
| `REJECTED` | Unsupported, irrelevant, insufficient, unreadable, or otherwise unusable content. |
| `FAILED` | A processing or system failure, not a judgment about the document’s quality. |

Minor editorial issues should not prevent useful knowledge from being available. Ambiguous or materially misleading content should never be published merely because an LLM produced a plausible summary.

### LLMs provide intelligence; application code owns orchestration

I use the LLM for semantic work: topic and claim extraction, relevance judgment, and structured quality findings. Application code owns every consequential action: validation order, lifecycle transitions, routing, retries, persistence, duplicate handling, correction application, indexing, and publication. Model output is structured and schema-validated before use. It informs the workflow; it does not control it.

The model never changes a document status, writes arbitrary database state, controls retries, or decides publication on its own. LLMs are probabilistic; state changes must be predictable, testable, and auditable. A provider change or malformed response cannot silently change lifecycle behavior. Invalid output fails safely.

## 5. Human-in-the-loop review design

I intentionally did not turn missing titles into a review workflow. Titles are optional metadata, not a reason to stop a learning resource from becoming useful. The platform derives a fallback from the filename and can use a Markdown heading when present.

Contributor review is reserved for safe, visible corrections. The current deterministic correction detects an immediately repeated word. The contributor sees the current and suggested values and chooses to accept or decline.

Acceptance applies the correction to extracted content, transitions the document to approval, and indexes it in the same transactional decision flow. Decline transitions it to rejection and removes any chunks. Repeating the same action is idempotent, and the unique `(document_id, position)` chunk constraint protects against duplicate publication.

Admin review represents a different class of uncertainty: a material semantic finding, contradiction, or factual concern. It deliberately offers no contributor “fix” button because resolving such a concern requires judgment beyond a mechanical edit. Admin-review documents are not searchable.

## 6. Ingestion, storage, and lifecycle data

I used Docling rather than creating a parser. For PDFs, OCR is disabled: a scanned source fails clearly instead of contributing guessed extraction. Markdown and text are decoded directly into a normalized document representation.

Uploaded bytes are stored under generated keys rather than user filenames. The original filename is metadata, not a filesystem path. Docker Compose mounts a named source-storage volume at the configured storage root, so recreating the backend does not orphan source records. PostgreSQL remains the system of record for document metadata, findings, analysis, review decisions, and lifecycle state.

Exact duplicate detection is content identity, not presentation identity. The service calculates SHA-256 from the uploaded bytes before expensive processing. Same bytes under a different filename are duplicates; the same filename with changed bytes is a new submission. Active and approved duplicates are rejected. Rejected and failed submissions are intentionally retryable: their old source and chunks are removed before the new version is stored. Filename comparison was rejected because it would both reject legitimate revisions and miss identical files with different names.

Documents and chunks are separate records. Chunks carry position, text, source context, embedding metadata, and a 384-dimensional vector. A foreign key with cascade deletion and a unique document-position constraint preserve publication integrity. Alembic migrations create the lifecycle, review, source-storage, grounded-verification, and vector schema.

## 7. Retrieval and answer generation

Search uses PostgreSQL full-text retrieval and pgvector cosine similarity over BGE embeddings. Lexical retrieval is valuable for exact terminology; vector retrieval is valuable when a user uses different wording. I rejected vector-only retrieval because it can miss exact terms, and lexical-only retrieval because it can miss paraphrases. Combining both improves recall without reducing the product to filename search.

Precision is the more important trade-off for this product. A broad keyword fallback was removed because it turned incidental word overlap into false results. Vector candidates must pass a configurable similarity floor, and the lexical path removes weak tail matches relative to the strongest hit. Approved status is enforced in both retrieval queries, not merely hidden in the frontend.

The answer endpoint reuses retrieval rather than creating a second search path. It selects approved chunks, bounds assembled context to 12,000 characters, and asks the configured Gemini client to answer only from that context. Supporting resource cards are returned alongside the answer so users can see the reviewed material behind it.

The current release intentionally has a reviewed-only answer policy. This product is not trying to be a general chatbot; its value is that users know where an answer comes from. If retrieval finds no sufficiently relevant approved knowledge, it says so rather than using general model knowledge. I give up some answer coverage to keep a clear trust boundary and prevent users from confusing reviewed and unreviewed information. A clearly labelled model-knowledge fallback may be useful later. The prompt requires partial answers to say what is not covered, and the UI renders the complete Markdown answer rather than clipping it.

## 8. LLM and external verification

The backend uses the Google GenAI SDK with a configurable Gemini Flash model (the current default is `gemini-3.6-flash`). I chose it for structured JSON output, practical latency for an interactive vertical slice, and a simple provider boundary. Pydantic validates analysis, claim, and answer outputs before application code uses them.

Google Search Grounding is used selectively for time-sensitive or externally verifiable claims. It collects evidence; application code makes the final route. External verification can be quota-limited or unavailable, so an outage means missing additional evidence, not automatic invalidity. Provider errors are mapped to safe application errors and sanitized logs. The UI never receives a raw SDK object, provider payload, credential, or provider error detail.

I considered Claude, OpenAI models, and a separate external-search provider. They may be reasonable alternatives, but changing provider would not improve the core architectural choice. The useful boundary is the typed client contract, not a provider-specific abstraction hierarchy.

## 9. Frontend and UX decisions

The frontend is a React and TypeScript single-page product surface, not an operations dashboard. TanStack Query owns server state for uploads, polling, reviews, and search; local state is limited to file selection, input, disclosure, and presentation concerns. React Dropzone, Sonner, Lucide, Framer Motion, and React Markdown are used where those libraries remove commodity work.

The UX priority is legible state. Uploading clears the prior outcome; polling stops at terminal states; decision actions guard repeated requests; accepting or declining a review removes stale controls, resets the upload surface, and confirms the outcome. Errors are plain and actionable. Search hides stale answers while a new request is in flight and disables repeated submission until it finishes.

The dark HUD aesthetic is intentional but secondary. The important UX decisions are progressive disclosure of requirements, distinct terminal outcomes, visible review reasons, full answer rendering, keyboard-operable controls, responsive layouts, and reduced-motion behavior.

## 10. Technology and architecture choices

I chose a modular FastAPI monolith because document ingestion, review decisions, retrieval, and persistence need clear transaction boundaries more than service distribution. FastAPI and Pydantic provide typed HTTP contracts and fit the Python parsing and ML ecosystem without a heavy framework layer. Routes remain thin; services coordinate parsing, quality evaluation, review, indexing, and retrieval.

I chose PostgreSQL with pgvector because lifecycle state, metadata, lexical search, and embeddings need transactional consistency. I rejected a separate vector database because it adds operational complexity and synchronization risk with little value at this project scale. PostgreSQL full-text search and cosine vector search cover the required retrieval behavior, while the HNSW index leaves room to grow beyond a demo dataset.

Docker provides reproducible local behavior and packages the CPU-only BGE model plus Docling artifacts needed for offline digital-PDF parsing. The image is larger and slower to build than a thin API container; that trade-off avoids runtime Hugging Face downloads. Compose persists database and source-storage volumes across backend recreation.

## 11. Reliability and failure handling

The API has a typed error envelope and maps domain failures to user-safe messages. Known failures such as unsupported type, unreadable PDF, duplicate submission, invalid lifecycle transition, and search failure remain explicit. Unexpected failures use a generic safe message. Processing failure is recorded as `FAILED`, preserving the distinction from a quality rejection.

Multi-step contributor decisions are transactional: failed decisions roll back, and a successful approval indexes once. The ingestion path removes stored-source data if database persistence fails. Search is restricted to approved documents at query time, which protects retrieval even if a UI state is stale.

The deliberate limitation is background execution. FastAPI `BackgroundTasks` keeps uploads responsive and is acceptable for a single-instance demo, but it is not a durable queue. A process failure can interrupt accepted work. I deferred a worker queue because it is the correct production choice but too much operational scope for five days. The next production step is a durable worker and queue with idempotent jobs, visibility, and retry policy.

## 12. Alternatives considered and rejected

| Decision | Alternative | Trade-off accepted |
| --- | --- | --- |
| Trust engine | Broader parsing/OCR product | Less format breadth; mature tools already solve much of parsing, while admission trust is the harder product problem. |
| Hybrid retrieval | Vector-only or lexical-only retrieval | More query logic; better exact-term and paraphrase behavior. |
| PostgreSQL + pgvector | Separate vector database | Fewer specialized scaling options; one consistent system of record without synchronization risk. |
| Explicit correction consent | Silent auto-fixes | One extra decision; preserves contributor ownership. |
| Reviewed-only answers | Model-only fallback | Lower answer coverage; users never confuse reviewed and unreviewed information. |
| Digital PDF, Markdown, text | Broad format support | Narrower intake; reliable, testable behavior. |
| Background task boundary | Durable worker queue | Not durable across process failure; acceptable single-instance demo scope. |

## 13. What I would do next

1. Replace in-process background work with a durable queue and worker, including idempotency and operational visibility.
2. Build an admin-review workspace for resolving material concerns without bypassing the publication boundary.
3. Add retrieval evaluation data, richer reranking, and measured threshold tuning rather than heuristic expansion.
4. Add scanned-PDF support only when the OCR quality path can be evaluated and explained reliably.
5. Add authentication, tenancy, object storage, observability, and deployment hardening for a shared production service.
6. Consider an explicitly labelled model-knowledge fallback only after the reviewed and non-reviewed answer modes can be kept unmistakably separate.
