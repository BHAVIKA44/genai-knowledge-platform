from functools import lru_cache

from sentence_transformers import SentenceTransformer

QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIMENSIONS = 384


class EmbeddingInputError(ValueError):
    pass


class EmbeddingOutputError(ValueError):
    pass


class EmbeddingProviderError(Exception):
    pass


class DocumentEmbedder:
    def __init__(self, batch_size: int = 16) -> None:
        self.batch_size = batch_size

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts or any(not text.strip() for text in texts):
            raise EmbeddingInputError("Embedding input must contain text.")
        try:
            vectors = (
                get_embedding_model()
                .encode(texts, batch_size=self.batch_size, normalize_embeddings=True)
                .tolist()
            )
        except Exception as error:
            raise EmbeddingProviderError("Local embedding generation failed.") from error
        if any(len(vector) != EMBEDDING_DIMENSIONS for vector in vectors):
            raise EmbeddingOutputError("Embedding model returned an unexpected dimension.")
        return [[float(value) for value in vector] for vector in vectors]

    def embed_query(self, text: str) -> list[float]:
        if not text.strip():
            raise EmbeddingInputError("Embedding input must contain text.")
        prefix = "" if text.startswith(QUERY_PREFIX) else QUERY_PREFIX
        return self.embed_documents([prefix + text])[0]


@lru_cache
def get_embedding_model() -> SentenceTransformer:
    return SentenceTransformer(EMBEDDING_MODEL, device="cpu")
