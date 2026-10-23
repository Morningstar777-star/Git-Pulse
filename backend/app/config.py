import os
from pathlib import Path
from dotenv import load_dotenv

# Base paths
BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent

# Load .env if present
env_path = PROJECT_ROOT / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    load_dotenv()

# Configuration Settings
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "").strip()
TURSO_DATABASE_URL = os.getenv("TURSO_DATABASE_URL", "").strip()
TURSO_AUTH_TOKEN = os.getenv("TURSO_AUTH_TOKEN", "").strip()

# Resilient Database Path Resolution (supports local dev, Docker, and Vercel Serverless)
_default_db_path = PROJECT_ROOT / "data" / "gitpulse.db"
if not _default_db_path.exists():
    # Fallback to backend/data or current directory
    alt_path = BACKEND_DIR / "data" / "gitpulse.db"
    if alt_path.exists():
        _default_db_path = alt_path

# On Vercel serverless, /var/task is read-only; copy bundled SQLite database to /tmp so writes succeed
if os.getenv("VERCEL") or os.getenv("AWS_LAMBDA_FUNCTION_NAME"):
    import shutil
    tmp_dir = Path("/tmp")
    tmp_db = tmp_dir / "gitpulse.db"
    if not tmp_db.exists() and _default_db_path.exists():
        try:
            tmp_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(_default_db_path), str(tmp_db))
        except Exception as e:
            print(f"[Config] Notice: Could not copy DB to /tmp ({e}); using bundled path.")
    if tmp_db.exists():
        _default_db_path = tmp_db

DB_PATH = os.getenv("DB_PATH", str(_default_db_path))
REFRESH_INTERVAL_MINUTES = int(os.getenv("REFRESH_INTERVAL_MINUTES", "60"))
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
FRONTEND_DIST_DIR = PROJECT_ROOT / "frontend" / "dist"
