"""
Quick ingest test: index first N files only.
Run: uv run python -m ingest.test_ingest
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

from config.settings import PROJECT_ROOT, settings
from ingest.chunk import chunk_text
from ingest.repo import ensure_repo, list_files

# Embedding model: same as main ingest
EMBED_MODEL = "BAAI/bge-small-en-v1.5"
BATCH_SIZE = 64

# Test limits
MAX_FILES = 20  # Only index first 20 files


def main() -> None:
    # Use test index path under repo root so it's always the same folder
    index_dir = PROJECT_ROOT / "data" / "faiss_index_test"
    index_dir.mkdir(parents=True, exist_ok=True)
    index_file = index_dir / "index.faiss"
    meta_file = index_dir / "metadata.json"

    repo_path = ensure_repo(settings.repo_path)
    print(f"Repo: {repo_path}")
    print(f"TEST MODE: Indexing first {MAX_FILES} files only")

    from sentence_transformers import SentenceTransformer

    print("Loading embedding model...")
    model = SentenceTransformer(EMBED_MODEL)
    tokenizer = model.tokenizer
    try:
        tokenizer.model_max_length = 1_000_000
    except Exception:
        pass

    files = list_files(repo_path)[:MAX_FILES]  # Limit files
    print(f"Files to index: {len(files)} (limited from full repo)")

    chunks_with_meta: list[tuple[str, str, int]] = []
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

    faiss.write_index(index, str(index_file))
    metadata = [
        {"path": p, "text": t, "chunk_id": c}
        for (p, t, c) in chunks_with_meta
    ]
    meta_file.write_text(json.dumps(metadata, indent=0), encoding="utf-8")

    size_mb = index_file.stat().st_size / (1024 * 1024)
    print(f"✅ TEST INDEX SAVED: {index_file} ({size_mb:.2f} MB), {meta_file} ({len(metadata)} chunks)")
    print("To use this test index, set INDEX_PATH=./data/faiss_index_test in .env")


if __name__ == "__main__":
    main()
    sys.exit(0)
