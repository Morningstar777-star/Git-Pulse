import os
import ssl
import certifi

# Fix for Windows cert store ASN1 corrupted cert bug: use certifi CA bundle
_orig_create_default_context = ssl.create_default_context
def _safe_create_default_context(*args, **kwargs):
    if "cafile" not in kwargs:
        kwargs["cafile"] = certifi.where()
    return _orig_create_default_context(*args, **kwargs)
ssl.create_default_context = _safe_create_default_context

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import FRONTEND_DIST_DIR
from app.database import init_db_sync, get_sync_connection
from app.seed_data import seed_database_if_empty
from app.scheduler import scheduler
from app.routes import repositories, momentum, topics, watchlist, status, auth

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Startup: Initialize SQLite DB schema
    print("[GitPulse] Initializing local SQLite database...")
    init_db_sync()
    
    # 2. Seed baseline dataset if empty
    with get_sync_connection() as conn:
        count = seed_database_if_empty(conn)
        print(f"[GitPulse] Database ready. Active repositories: {count}")

    # 3. Start background crawler scheduler
    await scheduler.start()

    yield

    # 4. Shutdown: Cancel scheduler
    print("[GitPulse] Shutting down scheduler...")
    await scheduler.stop()

app = FastAPI(
    title="GitPulse Explorer API",
    description="Local GitHub Trend Intelligence & Momentum Radar",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for local Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Cybersecurity hardening: HTTP response security headers
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "SAMEORIGIN"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# Include API Routers
app.include_router(repositories.router)
app.include_router(momentum.router)
app.include_router(topics.router)
app.include_router(watchlist.router)
app.include_router(status.router)
app.include_router(auth.router)

# Serve built frontend static files locally (On Vercel, static files are served by Vercel CDN)
if not os.getenv("VERCEL") and FRONTEND_DIST_DIR.exists() and (FRONTEND_DIST_DIR / "index.html").exists():
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST_DIR / "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Don't intercept API routes
        if full_path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        file_path = FRONTEND_DIST_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        return FileResponse(FRONTEND_DIST_DIR / "index.html")
else:
    @app.get("/")
    async def root():
        return {
            "name": "GitPulse Explorer API",
            "status": "ONLINE",
            "message": "GitPulse Explorer Serverless API Active",
            "api_docs": "/docs"
        }
            "api_docs": "/docs"
        }
