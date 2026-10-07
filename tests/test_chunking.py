from ingestion.hr.chunking import chunk_text


def test_table_stays_atomic():
    table = "\n".join("| a | b |" for _ in range(50))
    text = "intro\n\n" + table + "\n\noutro"
    chunks = chunk_text(text, chunk_size=20, overlap=0)
    assert any(table in c for c in chunks)


def test_oversized_text_gets_split():
    text = "word " * 2000
    chunks = chunk_text(text, chunk_size=50, overlap=10)
    assert len(chunks) > 1


def test_empty_text_returns_no_chunks():
    assert chunk_text("") == []


def test_short_text_is_single_chunk():
    chunks = chunk_text("just a short paragraph", chunk_size=1024, overlap=200)
    assert len(chunks) == 1
