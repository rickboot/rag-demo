#!/bin/bash
# Quick test ingest: indexes first 20 files only
# Usage: ./ingest/test_ingest.sh

uv run python -m ingest.test_ingest
