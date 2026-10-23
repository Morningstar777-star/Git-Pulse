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
from starlette.middleware.base import BaseHTTPMiddleware

class VercelPathMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # Prefer original client URL headers forwarded by Vercel CDN/routing layer
        raw_path = (
            request.headers.get("x-matched-path")
            or request.headers.get("x-forwarded-uri")
            or request.headers.get("x-original-uri")
            or request.scope.get("path", "")
        )
        path = raw_path.split("?")[0] if raw_path else ""

        # Normalize any internal /index.py references to clean /api path
        if "index.py" in path:
            idx = path.find("index.py")
            after = path[idx + len("index.py"):]
            if after.startswith("/"):
                path = "/api" + after if not after.startswith("/api") else after
            else:
                path = "/" if not after else after

        if path:
            request.scope["path"] = path

        return await call_next(request)

fastapi_app.add_middleware(VercelPathMiddleware)

# Explicitly export the FastAPI instance as 'app' for Vercel
app = fastapi_app
