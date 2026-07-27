FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0t64 libxcb1 \
    && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch torchvision
COPY . .
RUN pip install --no-cache-dir .
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5', device='cpu')"
RUN python -c "from huggingface_hub import snapshot_download; [snapshot_download(repo_id, revision=revision) for repo_id, revision in [('docling-project/docling-layout-heron', 'main'), ('docling-project/docling-models', 'v2.3.0'), ('docling-project/CodeFormulaV2', 'main')]]"

ENV HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
