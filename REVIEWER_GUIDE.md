# GenAI Knowledge Platform — Reviewer Guide

## What this product does

GenAI Knowledge Platform is a trusted knowledge base for Generative AI learning material. Users upload resources, the Knowledge Quality Engine reviews them, and only accepted material becomes searchable. The focus is knowledge trust and quality, not simply extracting text from messy documents.

## Recommended setup

- Use a laptop or desktop browser for the best experience.
- Chrome is recommended.
- The deployed application is intended as a single-user MVP.

## Quick test flow

1. Open **Add Knowledge**.
2. Upload a supported GenAI PDF, Markdown, or TXT resource.
3. Leave the title empty or provide one.
4. Wait while the system reviews the resource.
5. Complete contributor review if a small deterministic correction is proposed.
6. Search for a concept contained in an accepted resource and inspect the supporting evidence.

## What the review outcomes mean

- **Approved:** Trusted and searchable.
- **Contributor review:** A small, safe correction requires the uploader’s decision.
- **Admin review:** The material requires stronger human judgment and is not searchable yet.
- **Rejected:** Outside scope or unsuitable as a GenAI learning resource.
- **Failed:** Processing could not complete safely and may be retried.

## Useful scenarios to try

- Upload a valid GenAI learning resource.
- Upload useful but slightly messy material.
- Accept or decline a small correction.
- Upload non-GenAI content and confirm it is rejected.
- Upload an accepted resource again and confirm the duplicate is blocked.

## Current MVP boundaries

- Supports digital PDF, Markdown, and TXT.
- Scanned PDFs and OCR are intentionally outside the MVP.
- Maximum upload size is 10 MB.
- PDFs are limited to 50 pages.
- Content requires at least 150 meaningful characters.
- Search answers are based only on accepted, reviewed knowledge.
- General model-only fallback is intentionally not included in this 5 day exercise.

## Links

- Live application: https://genai-knowledge-platform.vercel.app
- GitHub repository: https://github.com/BHAVIKA44/genai-knowledge-platform
- API documentation: https://genai-knowledge-platform-production.up.railway.app/docs
