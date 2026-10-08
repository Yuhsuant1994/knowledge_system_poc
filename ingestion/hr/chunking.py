import tiktoken

ENCODING = tiktoken.get_encoding("cl100k_base")


def _is_table_line(line: str) -> bool:
    """Check whether a line looks like it belongs to a table."""
    return "|" in line or "\t" in line


def _split_segments(text: str) -> list[tuple[bool, str]]:
    """Split text into alternating table and non-table segments.

    Args:
        text: The raw text to split, using newlines as line separators.

    Returns:
        A list of (is_table, content) tuples, where consecutive table
        lines are grouped together and consecutive non-table lines are
        grouped together, preserving their original order.
    """
    segments = []
    buf, table_buf = [], []
    in_table = False

    for line in text.split("\n"):
        if _is_table_line(line.strip()):
            if not in_table and buf:
                segments.append((False, "\n".join(buf)))
                buf = []
            in_table = True
            table_buf.append(line)
        else:
            if in_table:
                segments.append((True, "\n".join(table_buf)))
                table_buf = []
                in_table = False
            buf.append(line)

    if in_table and table_buf:
        segments.append((True, "\n".join(table_buf)))
    if buf:
        segments.append((False, "\n".join(buf)))
    return segments


def chunk_text(text: str, chunk_size: int = 1024, overlap: int = 200) -> list[str]:
    """Split text into token-bounded chunks with overlap, keeping tables intact.

    Text is first split into table and non-table segments. Segments are
    packed into chunks up to ``chunk_size`` tokens, tables are never split
    across chunks, and oversized plain-text segments are hard-split on
    token boundaries. Each resulting chunk (after the first) is prefixed
    with a tail of overlapping tokens from the previous chunk.

    Args:
        text: The text to chunk.
        chunk_size: Maximum number of tokens per chunk.
        overlap: Number of trailing tokens from the previous chunk to
            prepend to each subsequent chunk.

    Returns:
        The list of non-empty text chunks.
    """
    chunks = []
    current, current_tokens = [], 0

    def flush():
        """Append the buffered lines as a chunk and reset the buffer."""
        nonlocal current, current_tokens
        if current:
            chunks.append("\n".join(current).strip())
            current, current_tokens = [], 0

    for is_table, content in _split_segments(text):
        if not content.strip():
            continue
        tokens = ENCODING.encode(content)
        # handling table like format, forcing table to not be split to different doc
        if is_table or len(tokens) <= chunk_size:
            if current_tokens + len(tokens) > chunk_size:
                flush()
            current.append(content)
            current_tokens += len(tokens)
            continue

        flush()  # oversized plain-text segment: hard-split on tokens
        for start in range(0, len(tokens), chunk_size):
            chunks.append(ENCODING.decode(tokens[start : start + chunk_size]).strip())

    flush()

    result = []
    for i, chunk in enumerate(chunks):
        if i == 0:
            result.append(chunk)
            continue
        prev_tokens = ENCODING.encode(chunks[i - 1])
        tail = prev_tokens[-overlap:] if len(prev_tokens) > overlap else prev_tokens
        result.append((ENCODING.decode(tail) + "\n" + chunk).strip())
    return [c for c in result if c]
