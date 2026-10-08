from functools import lru_cache

from langchain_ollama import OllamaEmbeddings

from api.config import settings


@lru_cache(maxsize=1)
def _client() -> OllamaEmbeddings:
    """Build (and cache) the shared Ollama embeddings client.

    Returns:
        A singleton `OllamaEmbeddings` instance configured from settings.
    """
    return OllamaEmbeddings(
        base_url=settings.ollama_base_url, model=settings.embedding_model
    )


def embed(texts: list[str]) -> list[list[float]]:
    """Embed a batch of documents.

    Args:
        texts: Document strings to embed.

    Returns:
        One embedding vector per input text, in the same order.
    """
    return _client().embed_documents(texts)


def embed_one(text: str) -> list[float]:
    """Embed a single query string.

    Args:
        text: The query text to embed.

    Returns:
        The embedding vector for the query.
    """
    return _client().embed_query(text)


# pgvector text input format, e.g. "[0.1,0.2,0.3]" -- cast with CAST(:param AS vector)
def to_pgvector_literal(values: list[float]) -> str:
    """Format a vector as a pgvector text literal.

    Args:
        values: The embedding components.

    Returns:
        A string like "[0.1,0.2,0.3]" suitable for CAST(:param AS vector).
    """
    return "[" + ",".join(repr(v) for v in values) + "]"
