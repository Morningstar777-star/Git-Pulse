import sqlite3
import aiosqlite
from pathlib import Path
from typing import Optional
from app.config import DB_PATH, TURSO_DATABASE_URL, TURSO_AUTH_TOKEN
from app.turso_client import TursoClient, TursoConnection

_turso_client = None
if TURSO_AUTH_TOKEN and TURSO_DATABASE_URL:
    try:
        _turso_client = TursoClient(TURSO_DATABASE_URL, TURSO_AUTH_TOKEN)
        print(f"[Database] Active backend: Turso Cloud Database ({TURSO_DATABASE_URL})")
    except Exception as e:
        print(f"[Database] Notice: Turso initialization skipped ({e}); falling back to local SQLite.")

def init_db_sync():
    """Synchronously initialize SQLite database tables and indexes."""
    global _turso_client
    if _turso_client:
        try:
            _turso_client.init_schema()
            print("[Database] Remote Turso schema initialized.")
        except Exception as e:
            print(f"[Database] Notice: Turso schema check ({e})")

    db_file = Path(DB_PATH)
    try:
        db_file.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(db_file))
        cursor = conn.cursor()
    except Exception as e:
        print(f"[Database] Notice: Local SQLite file connection skipped ({e})")
        return
    
    # 1. Repositories table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS repositories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        owner TEXT NOT NULL,
        html_url TEXT NOT NULL,
        description TEXT,
        language TEXT,
        topics TEXT, -- JSON array string
        stars INTEGER DEFAULT 0,
        forks INTEGER DEFAULT 0,
        open_issues INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        pushed_at TEXT,
        category_id TEXT NOT NULL,
        is_emerging BOOLEAN DEFAULT 0,
        last_crawled_at TEXT
    );
    """)
    
    # 2. Historical Star/Activity Snapshots
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        repo_id INTEGER NOT NULL,
        timestamp TEXT NOT NULL,
        stars INTEGER NOT NULL,
        forks INTEGER DEFAULT 0,
        open_issues INTEGER DEFAULT 0,
        delta_stars_24h REAL DEFAULT 0,
        delta_stars_7d REAL DEFAULT 0,
        delta_stars_30d REAL DEFAULT 0,
        FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE
    );
    """)
    
    # 3. Watchlist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS watchlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        repo_id INTEGER UNIQUE NOT NULL,
        added_at TEXT NOT NULL,
        notes TEXT,
        FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE
    );
    """)

    # 4. Crawl & Ingestion History
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS crawl_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        started_at TEXT NOT NULL,
        finished_at TEXT,
        status TEXT NOT NULL,
        repos_updated INTEGER DEFAULT 0,
        rate_limit_remaining INTEGER,
        error_message TEXT
    );
    """)

    # 5. Model Evaluation Benchmarks
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS model_benchmarks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        model_name TEXT NOT NULL,
        evaluated_at TEXT NOT NULL,
        ndcg_10 REAL NOT NULL,
        precision_10 REAL NOT NULL,
        spearman_corr REAL NOT NULL,
        mae REAL NOT NULL,
        description TEXT
    );
    """)

    # 6. Persistent Translation Cache for CJK text
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS translations (
        source_text TEXT PRIMARY KEY,
        translated_text TEXT NOT NULL,
        source_lang TEXT DEFAULT 'cjk',
        created_at TEXT NOT NULL
    );
    """)

    # 7. User Accounts (Optional Sign-In & Bookmarks)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        name TEXT NOT NULL,
        reset_token TEXT,
        reset_code TEXT,
        reset_expires_at TEXT,
        created_at TEXT NOT NULL
    );
    """)

    # 8. User Auth Sessions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );
    """)

    # 9. Per-User Watchlist / Bookmarks
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS user_watchlist (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        repo_id INTEGER NOT NULL,
        added_at TEXT NOT NULL,
        notes TEXT,
        UNIQUE(user_id, repo_id),
        FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY (repo_id) REFERENCES repositories(id) ON DELETE CASCADE
    );
    """)

    # Migration: Ensure description_en column exists on repositories
    cursor.execute("PRAGMA table_info(repositories);")
    columns = [col[1] for col in cursor.fetchall()]
    if "description_en" not in columns:
        cursor.execute("ALTER TABLE repositories ADD COLUMN description_en TEXT;")

    # Create Indexes for high-speed queries
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_repos_cat ON repositories(category_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_repos_stars ON repositories(stars DESC);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_repos_lang ON repositories(language);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_repos_name ON repositories(name);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_snapshots_repo ON snapshots(repo_id, timestamp);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_user_watchlist ON user_watchlist(user_id, repo_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);")
    
    try:
        conn.commit()
        conn.close()
    except sqlite3.OperationalError as e:
        print(f"[Database] Notice: SQLite schema sync skipped ({e}). Operating in read-only mode.")
    except Exception as e:
        print(f"[Database] Notice during schema sync: {e}")

async def get_db_connection():
    """Async connection generator for FastAPI dependencies. Uses Turso if configured, else local SQLite."""
    global _turso_client
    if _turso_client:
        yield TursoConnection(_turso_client)
        return

    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    try:
        yield conn
    finally:
        await conn.close()

def get_sync_connection():
    """Synchronous connection for scripts and offline pipelines."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn
