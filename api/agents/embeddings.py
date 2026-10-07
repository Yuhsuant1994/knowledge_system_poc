from functools import lru_cache

from langchain_ollama import OllamaEmbeddings

from api.config import settings


@lru_cache(maxsize=1)
def _client() -> OllamaEmbeddings:
    return OllamaEmbeddings(
        base_url=settings.ollama_base_url, model=settings.embedding_model
    )


def embed(texts: list[str]) -> list[list[float]]:
    return _client().embed_documents(texts)


def embed_one(text: str) -> list[float]:
    return _client().embed_query(text)


# pgvector text input format, e.g. "[0.1,0.2,0.3]" -- cast with CAST(:param AS vector)
def to_pgvector_literal(values: list[float]) -> str:
    return "[" + ",".join(repr(v) for v in values) + "]"
