"""Run ingest: uv run python -m ingest"""

import sys

from ingest.run import main

if __name__ == "__main__":
    main()
    sys.exit(0)  # Force exit; avoid hanging on tokenizer/transformers cleanup
