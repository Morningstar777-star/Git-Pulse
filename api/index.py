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
        matched = request.headers.get("x-matched-path")
        if matched and not matched.endswith("index.py"):
            request.scope["path"] = matched
        elif request.headers.get("x-forwarded-uri"):
            fwd = request.headers.get("x-forwarded-uri").split("?")[0]
            if fwd and not fwd.endswith("index.py"):
                request.scope["path"] = fwd
        return await call_next(request)

fastapi_app.add_middleware(VercelPathMiddleware)

# Explicitly export the FastAPI instance as 'app' for Vercel
app = fastapi_app
