# Decisions

## 1. I chose to build a trusted knowledge system, not another document parser.

The project brief was about turning messy documents into structured, queryable data. Parsing is necessary, but mature libraries already solve much of extraction, OCR, chunking, and embeddings. Building another parser would mostly be engineering around solved problems. I chose to spend my time on a harder product question: how does a system decide what deserves to become trusted knowledge?

## 2. Good retrieval starts before retrieval.

A retrieval system cannot repair a poor knowledge base. If low-quality information is indexed, even the best search algorithm will confidently return wrong answers. I therefore treated knowledge admission as the core product problem instead of treating retrieval as the beginning of the pipeline.

## 3. The Knowledge Quality Engine is the product boundary.

Every uploaded document passes through deterministic validation, semantic analysis, and review before it can be indexed. The goal is not to process every document. The goal is to ensure only trusted knowledge influences future answers.

## 4. LLMs provide intelligence. Application code provides orchestration.

The LLM is responsible for understanding language, extracting claims, and producing structured findings. Application code owns validation order, lifecycle transitions, retries, persistence, indexing, publication, and every state change. Models should assist decisions, not control systems.

## 5. Deterministic checks should run before probabilistic reasoning.

File size, MIME type, page count, duplicate detection, language detection, and other objective validations run before any LLM call. Cheap and deterministic checks remove obvious failures early, reduce cost, and prevent the model from solving problems the application already knows how to solve.

## 6. Human review is part of the workflow, not a fallback.

The system only asks for human judgment when automation reaches its limit. Objective corrections stay with the contributor. Material ambiguity, contradictions, or factual concerns move to admin review. Automation should stop where judgment begins.

## 7. Only reviewed knowledge should influence answers.

The system retrieves information only from approved documents. I intentionally did not add a general model-knowledge fallback because I wanted every answer to have a clear provenance. I accepted lower answer coverage to preserve trust.

## 8. Retrieval quality determines answer quality.

Vector search and lexical search fail in different ways, so I combined both instead of choosing one. I optimized for precision over maximum recall because irrelevant context often leads to confident hallucinations. Better retrieval is often more valuable than a larger model.

## 9. Reliable systems grow by confidence, not by supported formats.

I intentionally started with digital PDFs, Markdown, and TXT because their extraction quality is predictable and measurable. OCR, scanned PDFs, HTML, and other formats introduce additional uncertainty. I would rather support fewer formats with consistent behavior than claim broad support without understanding extraction quality.

## 10. Technology choices should reduce operational complexity.

Every major technology decision was made to simplify the system rather than make it more impressive. PostgreSQL with pgvector keeps lifecycle state, metadata, lexical search, and vectors in one system. FastAPI fits naturally with the Python AI ecosystem. Gemini provided structured output and Google Search Grounding through one provider, allowing me to spend my limited time on the Knowledge Quality Engine instead of integrating additional search infrastructure. Docker ensures the runtime remains reproducible across environments.

## 11. Abstract volatility, not business logic.

I introduced abstractions around components that are likely to change, such as the LLM provider, parser, embeddings, and retrieval layer. Product rules like review decisions, lifecycle transitions, and publication logic remain explicit because they are the business itself, not replaceable infrastructure.

## 12. Reliability is a product feature.

Failures should be explicit and recoverable. The system distinguishes processing failures from quality rejections, contributor actions are transactional and idempotent, and publication happens exactly once. Users should always understand whether a document failed because of the system or because of the content.

## 13. The biggest production feature missing is evaluation, not another model.

The project includes representative manual testing and application-level tests, but I intentionally did not build a formal LLM evaluation framework within the scope of this exercise. A production system should continuously measure retrieval quality, groundedness, citation correctness, contradiction routing, and prompt-injection resilience using versioned benchmark datasets. A prompt or model change should not ship because a few examples looked better.

## 14. Prompt injection should be treated as a production engineering problem.

Uploaded documents, retrieved passages, and user questions should all be considered untrusted input. A production deployment would introduce instruction separation, context sanitization, adversarial evaluation, stricter document validation, and dedicated prompt-injection testing. This was intentionally left outside the MVP so I could focus on building a complete trusted-ingestion workflow first.

## 15. The next investment should be measurement, not more AI complexity.

Before adding OCR, more document formats, reranking, or unrestricted model knowledge, I would first invest in evaluation, retrieval observability, durable workers, structured feedback loops, and operational reliability. Better measurement makes every future improvement safer.

## 16. Users should experience determinism, even if the model is probabilistic.

An LLM may generate different outputs for the same input, but the surrounding application should always produce consistent behavior. Structured outputs, validation, lifecycle management, and deterministic business rules ensure that the user interacts with a reliable system rather than directly with a probabilistic model.

## 17. Good UX reduces uncertainty, not just clicks.

The UI was designed to explain the system rather than simply display it. Uploads expose lifecycle states, review decisions are visible, long-running operations communicate progress, and answers show supporting reviewed resources instead of appearing as black-box responses.
