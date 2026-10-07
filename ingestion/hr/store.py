import tempfile
from pathlib import Path

from sqlalchemy import text

from api.agents.embeddings import embed, to_pgvector_literal
from api.db.session import engine
from ingestion.hr.chunking import chunk_text


def index_doc(source: str, title: str, content: str) -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp) / "doc.md"
        tmp_path.write_text(content)
        pieces = chunk_text(tmp_path.read_text())

    vectors = embed(pieces)
    rows = [
        {
            "id": f"{source}#{i}",
            "source": source,
            "text": f"{title}\n\n{piece}",
            "embedding": to_pgvector_literal(vector),
        }
        for i, (piece, vector) in enumerate(zip(pieces, vectors))
    ]

    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM hr_documents WHERE source = :source"), {"source": source}
        )
        if rows:
            conn.execute(
                text(
                    "INSERT INTO hr_documents (id, source, text, embedding) "
                    "VALUES (:id, :source, :text, CAST(:embedding AS vector))"
                ),
                rows,
            )
    return len(rows)


def delete_doc(source: str) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("DELETE FROM hr_documents WHERE source = :source"), {"source": source}
        )


def clear_all() -> None:
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM hr_documents"))
