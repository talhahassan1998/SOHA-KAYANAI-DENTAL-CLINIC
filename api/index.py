"""Vercel serverless entrypoint — Vercel's Python runtime imports `app` from here."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from run import app  # noqa: E402,F401
