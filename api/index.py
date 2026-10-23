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
        # 1. Query parameter fallback from Vercel rewrite
        route_param = request.query_params.get("__path")
        if route_param:
            target_path = "/api/" + route_param.lstrip("/")
            request.scope["path"] = target_path
            return await call_next(request)

        # 2. Check original URL headers forwarded by Vercel CDN/routing layer
        raw_path = (
            request.headers.get("x-matched-path")
            or request.headers.get("x-forwarded-uri")
            or request.headers.get("x-original-uri")
            or request.scope.get("path", "")
        )
        path = raw_path.split("?")[0] if raw_path else ""

        # 3. Normalize internal /index.py references
        if "index.py" in path:
            idx = path.find("index.py")
            after = path[idx + len("index.py"):].lstrip("/")
            if after:
                path = "/api/" + after if not after.startswith("api/") else "/" + after
            else:
                path = "/"

        if path and not path.endswith("index.py"):
            request.scope["path"] = path

        return await call_next(request)

fastapi_app.add_middleware(VercelPathMiddleware)

# Explicitly export the FastAPI instance as 'app' for Vercel
app = fastapi_app
