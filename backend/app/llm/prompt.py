PROMPT_VERSION = "v1"

KNOWLEDGE_EXTRACTION_PROMPT = """Analyze only the supplied GenAI learning document.
Return JSON with proposed_title, summary, topics, claims, and semantic_findings.
Each claim must include text,
confidence (from 0 to 1), is_time_sensitive, and requires_external_verification.
Each semantic finding must include category, severity (INFO, WARNING, or BLOCKING), confidence,
explanation, suggested_improvement, contributor_fix_possible, and admin_review_required.
Ground every result in the supplied text; do not add unsupported information or hidden reasoning.
Normalize GenAI topics, extract important technical claims, and
mark time-sensitive or future-verification claims. Identify only vague explanations,
missing context,
incomplete definitions, misleading wording, or technical ambiguity in the supplied document.

Document:
{text}"""

CLAIM_GROUNDING_PROMPT = """Verify the listed GenAI technical claims using Google Search grounding.
Do not decide document workflow or approval. Do not use hidden reasoning.
Return JSON with verifications. Each verification must include the original claim text, verdict
(SUPPORTED, PARTIALLY_SUPPORTED, NOT_SUPPORTED, or INSUFFICIENT_EVIDENCE), confidence from 0 to 1,
and a concise explanation grounded in the available evidence.

Claims:
{claims}"""
