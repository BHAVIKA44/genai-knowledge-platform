PROMPT_VERSION = "v1"

KNOWLEDGE_EXTRACTION_PROMPT = """Analyze only the supplied GenAI learning document.
Return JSON with proposed_title, summary, topics, and claims. Each claim must include text,
confidence (from 0 to 1), is_time_sensitive, and requires_external_verification.
Ground every result in the supplied text; do not add unsupported information or hidden reasoning.
Normalize GenAI topics, extract important technical claims, and
mark time-sensitive or future-verification claims.

Document:
{text}"""
