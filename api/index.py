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

from app.main import app as fastapi_app

class VercelPathNormalizationMiddleware:
    """
    Ensures that rewritten paths from Vercel Serverless (e.g. /api/index.py)
    are mapped back to their original target API routes using Vercel headers.
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            headers = dict(scope.get("headers", []))
            raw_path = scope.get("path", "")

            # Check Vercel original path headers
            matched_path = headers.get(b"x-matched-path", b"").decode("utf-8")
            if matched_path and not matched_path.endswith("index.py"):
                raw_path = matched_path
            else:
                forwarded_uri = headers.get(b"x-forwarded-uri", b"").decode("utf-8")
                if forwarded_uri and not forwarded_uri.endswith("index.py"):
                    raw_path = forwarded_uri.split("?")[0]

            # If path doesn't start with /api and is not root/docs, ensure /api prefix
            if not raw_path.startswith("/api") and raw_path not in ("/", "/docs", "/openapi.json"):
                raw_path = "/api" + raw_path

            scope["path"] = raw_path

        await self.app(scope, receive, send)

app = VercelPathNormalizationMiddleware(fastapi_app)
