"""Vercel / WSGI entrypoint for AptiForge.

Vercel looks for a Flask `app` in root files like server.py, app.py, or wsgi.py.
Our real app lives in backend/, so this module adds that folder to the path
and re-exports the Flask application.
"""

from __future__ import annotations

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parent / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from app import app  # noqa: E402  — backend/app.py

# Optional: help local `vercel dev` / gunicorn discover the same object
application = app
