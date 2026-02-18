"""Clone repo and list code files."""

import subprocess
from pathlib import Path


TRANSFORMERS_REPO = "https://github.com/huggingface/transformers.git"

# Directories to skip when indexing (optional; keeps index smaller for dev)
SKIP_DIRS = {"__pycache__", ".git", "tests", "docs", "docs_src"}

# Extensions to index
CODE_EXTENSIONS = {".py", ".md", ".rst", ".txt"}


def ensure_repo(path: Path, clone_url: str = TRANSFORMERS_REPO) -> Path:
    """Clone repo into path if it doesn't exist; return path."""
    path = path.expanduser().resolve()
    if path.exists() and (path / ".git").exists():
        return path
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["git", "clone", "--depth", "1", clone_url, str(path)],
        check=True,
        capture_output=True,
    )
    return path


def list_files(
    root: Path,
    *,
    skip_dirs: set[str] | None = None,
    extensions: set[str] | None = None,
) -> list[Path]:
    """List files under root, skipping given dirs and limiting to extensions."""
    skip_dirs = skip_dirs or SKIP_DIRS
    extensions = extensions or CODE_EXTENSIONS
    out: list[Path] = []
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        if any(part in skip_dirs for part in p.relative_to(root).parts):
            continue
        if p.suffix.lower() in extensions:
            out.append(p)
    return sorted(out)
