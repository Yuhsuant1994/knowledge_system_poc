from sqlalchemy import text

from api.agents.embeddings import embed_one, to_pgvector_literal
from api.agents.llm import get_llm
from api.db.session import engine

RAG_PROMPT = """You are an HR assistant answering from the PostHog company
handbook. Use ONLY the content below. If they don't contain the answer,

return fallback message, I do not find your answer from the HR portal,
please raise reach out to HR for your specific question.

Retrieved content:
{context}

Question: {question}

Answer:"""


def search(question: str, top_k: int = 3) -> list[dict]:
    vector_literal = to_pgvector_literal(embed_one(question))
    with engine.connect() as conn:
        rows = (
            conn.execute(
                text(
                    "SELECT text, source FROM hr_documents "
                    "ORDER BY embedding <=> CAST(:query_vector AS vector) "
                    "LIMIT :k"
                ),
                {"query_vector": vector_literal, "k": top_k},
            )
            .mappings()
            .all()
        )
    return [dict(row) for row in rows]


def answer(question: str) -> dict:
    hits = search(question)
    if not hits:
        return {
            "answer": "Nothing in the handbook covers that -- try rephrasing or contact HR directly.",
            "sources": [],
        }

    context = "\n\n".join(f"[{h['source']}] {h['text']}" for h in hits)
    prompt = RAG_PROMPT.format(context=context, question=question)
    response = get_llm().invoke(prompt)
    sources = sorted({h["source"] for h in hits})
    return {"answer": response.content, "sources": sources}
