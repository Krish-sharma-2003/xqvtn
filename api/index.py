"""Vercel entry point for the FastAPI backend.

Adds ``backend/`` to ``sys.path`` so ``app.main`` resolves, then re-exports
the ASGI application for Vercel's Python runtime.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.main import app
