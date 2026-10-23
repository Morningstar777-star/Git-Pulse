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
    # If running locally, initialize SQLite and run background scheduler
    if not os.getenv("VERCEL"):
        print("[GitPulse] Initializing local database & scheduler...")
        init_db_sync()
        try:
            conn = get_sync_connection()
            count = seed_database_if_empty(conn)
            conn.close()
            print(f"[GitPulse] Database ready. Active repositories: {count}")
        except Exception as e:
            print(f"[GitPulse] Seeding note: {e}")
        await scheduler.start()
    else:
        # On Vercel serverless, safely verify schema on remote cloud database
        try:
            init_db_sync()
        except Exception as e:
            print(f"[GitPulse] Serverless schema init notice: {e}")

    yield

    if not os.getenv("VERCEL"):
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

# Serve built frontend static files if present, else expose clean API root
if FRONTEND_DIST_DIR.exists() and (FRONTEND_DIST_DIR / "index.html").exists():
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
