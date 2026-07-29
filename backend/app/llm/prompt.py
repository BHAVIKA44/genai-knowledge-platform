PROMPT_VERSION = "v1"

KNOWLEDGE_EXTRACTION_PROMPT = """Analyze only the supplied GenAI learning document.
Return JSON with proposed_title, summary, topics, claims, and semantic_findings.
Each claim must include text,
confidence (from 0 to 1), is_time_sensitive, and requires_external_verification.
Each semantic finding must include category, severity (INFO, WARNING, or BLOCKING), confidence,
explanation, suggested_improvement, contributor_fix_possible, and admin_review_required.
Ground every result in the supplied text; do not add unsupported information or hidden reasoning.
Normalize GenAI topics, extract important technical claims, and
mark time-sensitive or future-verification claims. Ignore title absence and minor editorial
imperfections. Record a semantic finding only when the supplied text is materially misleading,
unsafe, contradictory, or too ambiguous to evaluate safely. Set admin_review_required to true
only for those material issues. Otherwise use INFO or WARNING for optional suggestions.

Document:
{text}"""

CLAIM_GROUNDING_PROMPT = """Verify the listed GenAI technical claims using Google Search grounding.
Do not decide document workflow or approval. Do not use hidden reasoning.
Return JSON with verifications. Each verification must include the original claim text, verdict
(SUPPORTED, PARTIALLY_SUPPORTED, NOT_SUPPORTED, or INSUFFICIENT_EVIDENCE), confidence from 0 to 1,
and a concise explanation grounded in the available evidence.

Claims:
{claims}"""

KNOWLEDGE_ANSWER_PROMPT = """Answer the user's question using only the reviewed knowledge below.
Start with a direct answer to the question, then explain only the details relevant to the
user's intent. Adapt the depth and structure to the question instead of summarizing every
source. Do not mention reviewed knowledge, sources, retrieval, chunks, prompts, databases,
providers, or internal processing. Do not use outside knowledge or invent facts.

If the available information answers only part of the question, state the supported part
clearly and say which part is not covered. Use concise Markdown only when it improves
readability. Complete every sentence and end the answer cleanly.
Return JSON with one field: answer.

Question:
{question}

Reviewed knowledge:
{context}"""
