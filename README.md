# GenAI Knowledge Platform

A focused learning-resource platform where submitted GenAI documents must pass deterministic quality checks before they can enter a shared knowledge base.

## First vertical slice

Upload one Markdown, plain-text, or digitally generated PDF file. The platform validates the upload, extracts its content, applies deterministic English and GenAI relevance checks, stores structured findings in PostgreSQL, and displays the final state in the web app.

This slice intentionally does not include authentication, review actions, embeddings, semantic search, Gemini, web grounding, OCR, URLs, images, or durable background jobs.

## Local setup

```bash
cp .env.example .env
docker compose up --build
```

In a second terminal, apply the database migration before uploading documents:

```bash
docker compose exec backend alembic upgrade head
```

Docker starts PostgreSQL and the API at `http://localhost:8000`. The database volume persists between runs.

Run the frontend separately:

```bash
cd frontend
npm install
npm run dev
```

To apply migrations manually when running the backend outside Docker:

```bash
cd backend
alembic upgrade head
```

## Checks

```bash
cd backend
python3.12 -m ruff format --check .
python3.12 -m ruff check .
python3.12 -m mypy app
python3.12 -m pytest

cd ../frontend
npm run format
npm run lint
npm run build
```
