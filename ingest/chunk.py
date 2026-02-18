"""Chunk text by token count with overlap. Uses tokenizer.encode/decode."""

# Align chunk size with embedding model max length (bge* is typically 512).
# This avoids silent truncation during embedding and keeps retrieval chunks consistent.
CHUNK_TOKENS = 512
OVERLAP_TOKENS = 80  # ~15%


def chunk_text(
    text: str,
    tokenizer,  # must have .encode() and .decode()
    chunk_size: int = CHUNK_TOKENS,
    overlap: int = OVERLAP_TOKENS,
) -> list[str]:
    """
    Split text into chunks of ~chunk_size tokens with overlap.
    """
    if not text.strip():
        return []
    enc = tokenizer.encode(text, add_special_tokens=False)
    if isinstance(enc, list):
        ids = enc
    else:
        ids = enc.input_ids
    # Handle batch dimension (e.g. BatchEncoding gives 2D)
    if ids and not isinstance(ids[0], int):
        ids = list(ids[0]) if hasattr(ids, "__getitem__") else list(ids)[0]
    else:
        ids = list(ids)
    if len(ids) <= chunk_size:
        return [text.strip()] if text.strip() else []
    step = chunk_size - overlap
    chunks: list[str] = []
    start = 0
    while start < len(ids):
        end = min(start + chunk_size, len(ids))
        chunk_ids = ids[start:end]
        chunk_text_str = tokenizer.decode(chunk_ids, skip_special_tokens=True)
        if chunk_text_str.strip():
            chunks.append(chunk_text_str.strip())
        start += step
        if start >= len(ids):
            break
    return chunks
