"""
Ingest pipeline: clone Transformers → chunk → embed → FAISS.
Run from repo root: uv run python -m ingest
"""
import os
import warnings

# Before any tokenizer/transformers imports
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
# Apply warning filters to subprocesses too (resource_tracker can warn from helper processes).
# Format: action:message:category:module:lineno
os.environ.setdefault(
    "PYTHONWARNINGS",
    "ignore:resource_tracker: There appear to be .* leaked semaphore objects.*:UserWarning:multiprocessing.resource_tracker:0",
)
warnings.filterwarnings("ignore", message=".*resource_tracker.*leaked semaphore.*", category=UserWarning)

import json
import sys
from pathlib import Path

from config import settings
from ingest.chunk import chunk_text
from ingest.repo import ensure_repo, list_files

# Embedding model: good quality, 512 max length, runs on CPU/MPS
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
BATCH_SIZE = 128  # Larger batch = faster encode on most machines


def main() -> None:
    index_dir = settings.index_path
    if index_dir.suffix:
        index_dir = index_dir.parent
    index_dir.mkdir(parents=True, exist_ok=True)
    index_file = index_dir / "index.faiss"
    meta_file = index_dir / "metadata.json"
    print(f"Index output: {index_dir.resolve()}")

    repo_path = ensure_repo(settings.repo_path)
    print(f"Repo: {repo_path}")

    from sentence_transformers import SentenceTransformer

    print("Loading embedding model...")
    model = SentenceTransformer(EMBED_MODEL)
    tokenizer = model.tokenizer
    # We intentionally tokenize long files for chunking; avoid max-length warnings.
    try:
        tokenizer.model_max_length = 1_000_000
    except Exception:
        pass

    files = list_files(repo_path)
    max_files = settings.ingest_max_files
    if max_files > 0:
        files = files[:max_files]
        print(f"Files to index: {len(files)} (capped by INGEST_MAX_FILES={max_files}; set 0 for full repo)")
    else:
        print(f"Files to index: {len(files)} (full repo)")

    chunks_with_meta: list[tuple[str, str, int]] = []  # (path, text, chunk_id)
    for fp in files:
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            print(f"  Skip {fp.relative_to(repo_path)}: {e}")
            continue
        rel = str(fp.relative_to(repo_path))
        for i, chunk in enumerate(chunk_text(text, tokenizer)):
            chunks_with_meta.append((rel, chunk, i))

    print(f"Chunks: {len(chunks_with_meta)}")

    if not chunks_with_meta:
        print("No chunks; nothing to save.")
        return

    texts = [t for (_, t, _) in chunks_with_meta]
    print("Embedding...")
    embeddings = model.encode(texts, batch_size=BATCH_SIZE, show_progress_bar=True)

    import faiss
    import numpy as np

    d = embeddings.shape[1]
    index = faiss.IndexFlatIP(d)
    faiss.normalize_L2(embeddings)
    index.add(embeddings.astype(np.float32))

    index_file.parent.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(index_file))
    metadata = [
        {"path": p, "text": t, "chunk_id": c}
        for (p, t, c) in chunks_with_meta
    ]
    meta_file.write_text(json.dumps(metadata, indent=0), encoding="utf-8")

    size_mb = index_file.stat().st_size / (1024 * 1024)
    print(f"Saved: {index_file} ({size_mb:.2f} MB), {meta_file} ({len(metadata)} chunks)")


if __name__ == "__main__":
    main()
    sys.exit(0)  # Force exit; avoid hanging on tokenizer/transformers cleanup
