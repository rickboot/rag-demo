"""RAG retrieval: load FAISS index + metadata, embed query, return top-k chunks."""

from pathlib import Path

from config import settings

# Must match ingest/run.py
EMBED_MODEL = "BAAI/bge-small-en-v1.5"

_index = None
_metadata = None
_model = None


def _index_dir() -> Path:
    p = settings.index_path.expanduser().resolve()
    return p.parent if p.suffix else p


def _index_path() -> Path:
    return _index_dir() / "index.faiss"


def _meta_path() -> Path:
    return _index_dir() / "metadata.json"


def _load() -> None:
    global _index, _metadata, _model
    if _index is not None:
        return
    import json
    import faiss
    import numpy as np
    from sentence_transformers import SentenceTransformer

    idx_path = _index_path()
    meta_path = _meta_path()
    if not idx_path.exists() or not meta_path.exists():
        raise FileNotFoundError(
            f"Index not found. Run: uv run python -m ingest (expects {idx_path} and {meta_path})"
        )
    _index = faiss.read_index(str(idx_path))
    _metadata = json.loads(meta_path.read_text(encoding="utf-8"))
    _model = SentenceTransformer(EMBED_MODEL)


def retrieve(query: str, top_k: int = 10) -> list[dict]:
    """
    Embed query, search FAISS, return list of {path, text, score}.
    Loads index and model on first call.
    """
    _load()
    import numpy as np
    q = _model.encode([query], normalize_embeddings=True).astype(np.float32)
    scores, ids = _index.search(q, min(top_k, len(_metadata)))
    out = []
    for i, idx in enumerate(ids[0]):
        if idx < 0 or idx >= len(_metadata):
            continue
        meta = _metadata[idx]
        out.append({
            "path": meta["path"],
            "text": meta["text"],
            "score": float(scores[0][i]),
        })
    return out
