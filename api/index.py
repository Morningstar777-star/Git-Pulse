"""
Vercel Serverless Function Entrypoint for GitPulse Explorer.
Exposes the FastAPI application to Vercel's ASGI runtime.
"""

import sys
import os
from pathlib import Path

# Add project root and backend directory to sys.path
current_dir = Path(__file__).resolve().parent
project_root = current_dir.parent
backend_dir = project_root / "backend"

if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from app.main import app

# Export app for Vercel
app = app
