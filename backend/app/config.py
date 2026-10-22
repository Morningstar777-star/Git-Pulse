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
DB_PATH = os.getenv("DB_PATH", str(PROJECT_ROOT / "data" / "gitpulse.db"))
REFRESH_INTERVAL_MINUTES = int(os.getenv("REFRESH_INTERVAL_MINUTES", "60"))
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))
FRONTEND_DIST_DIR = PROJECT_ROOT / "frontend" / "dist"
