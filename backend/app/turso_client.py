"""
Turso Cloud Database Client (libSQL over HTTP / Hrana v2).
Provides zero-dependency, serverless-optimized connection to Turso cloud databases.
"""

import requests
import json
from typing import List, Dict, Any, Optional, Tuple

class TursoClient:
    def __init__(self, db_url: str, auth_token: str, timeout: int = 20):
        # Normalize URL: libsql://foo.turso.io -> https://foo.turso.io
        clean_url = db_url.strip()
        if clean_url.startswith("libsql://"):
            clean_url = "https://" + clean_url[len("libsql://"):]
        elif not clean_url.startswith("http://") and not clean_url.startswith("https://"):
            clean_url = "https://" + clean_url
        
        self.base_url = clean_url.rstrip("/")
        self.pipeline_url = f"{self.base_url}/v2/pipeline"
        self.auth_token = auth_token.strip()
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Bearer {self.auth_token}",
            "Content-Type": "application/json"
        }

    def _convert_value(self, val: Any) -> Dict[str, Any]:
        if val is None:
            return {"type": "null"}
        elif isinstance(val, int):
            return {"type": "integer", "value": str(val)}
        elif isinstance(val, float):
            return {"type": "float", "value": val}
        elif isinstance(val, bool):
            return {"type": "integer", "value": "1" if val else "0"}
        else:
            return {"type": "text", "value": str(val)}

    def execute(self, sql: str, params: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """Execute a single SQL statement against Turso and return result rows as dictionaries."""
        stmt: Dict[str, Any] = {"sql": sql}
        if params:
            stmt["args"] = [self._convert_value(p) for p in params]

        payload = {
            "requests": [
                {"type": "execute", "stmt": stmt},
                {"type": "close"}
            ]
        }

        resp = requests.post(self.pipeline_url, headers=self.headers, json=payload, timeout=self.timeout)
        if resp.status_code != 200:
            raise Exception(f"Turso API Error ({resp.status_code}): {resp.text}")

        data = resp.json()
        results = data.get("results", [])
        if not results:
            return []

        first_res = results[0]
        if first_res.get("type") == "error":
            err = first_res.get("error", {})
            raise Exception(f"Turso SQL Error: {err.get('message', 'Unknown error')}")

        resp_obj = first_res.get("response", {})
        result_obj = resp_obj.get("result", {})
        cols = [c.get("name") for c in result_obj.get("cols", [])]
        rows = result_obj.get("rows", [])

        out = []
        for r in rows:
            row_dict = {}
            for idx, col_name in enumerate(cols):
                cell = r[idx]
                if cell.get("type") == "null":
                    val = None
                elif cell.get("type") == "integer":
                    val = int(cell.get("value"))
                elif cell.get("type") == "float":
                    val = float(cell.get("value"))
                else:
                    val = cell.get("value")
                row_dict[col_name] = val
            out.append(row_dict)
        return out

    def execute_batch(self, statements: List[str]) -> List[Any]:
        """Execute a list of DDL / SQL queries in an atomic pipeline batch."""
        requests_list = []
        for sql in statements:
            requests_list.append({"type": "execute", "stmt": {"sql": sql}})
        requests_list.append({"type": "close"})

        payload = {"requests": requests_list}
        resp = requests.post(self.pipeline_url, headers=self.headers, json=payload, timeout=self.timeout)
        if resp.status_code != 200:
            raise Exception(f"Turso API Error ({resp.status_code}): {resp.text}")

        data = resp.json()
        results = data.get("results", [])
        errors = []
        for idx, res in enumerate(results):
            if res.get("type") == "error":
                errors.append(f"Stmt {idx}: {res.get('error', {}).get('message')}")
        if errors:
            raise Exception("Turso Batch Errors: " + "; ".join(errors))
        return results

    def init_schema(self):
        """Create all tables and indexes on the Turso database."""
        schema_sqls = [
            """
            CREATE TABLE IF NOT EXISTS repositories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                owner TEXT NOT NULL,
                html_url TEXT NOT NULL,
                description TEXT,
                language TEXT,
                topics TEXT,
                stars INTEGER DEFAULT 0,
                forks INTEGER DEFAULT 0,
                open_issues INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                pushed_at TEXT,
                category_id TEXT NOT NULL,
                is_emerging BOOLEAN DEFAULT 0,
                last_crawled_at TEXT,
                description_en TEXT
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_id INTEGER NOT NULL,
                timestamp TEXT NOT NULL,
                stars INTEGER NOT NULL,
                forks INTEGER DEFAULT 0,
                open_issues INTEGER DEFAULT 0,
                delta_stars_24h REAL DEFAULT 0,
                delta_stars_7d REAL DEFAULT 0,
                delta_stars_30d REAL DEFAULT 0
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                repo_id INTEGER UNIQUE NOT NULL,
                added_at TEXT NOT NULL,
                notes TEXT
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS crawl_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                status TEXT NOT NULL,
                repos_updated INTEGER DEFAULT 0,
                rate_limit_remaining INTEGER,
                error_message TEXT
            );
            """,
            """
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
            """,
            """
            CREATE TABLE IF NOT EXISTS translations (
                source_text TEXT PRIMARY KEY,
                translated_text TEXT NOT NULL,
                source_lang TEXT DEFAULT 'cjk',
                created_at TEXT NOT NULL
            );
            """,
            """
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
            """,
            """
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL
            );
            """,
            """
            CREATE TABLE IF NOT EXISTS user_watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                repo_id INTEGER NOT NULL,
                added_at TEXT NOT NULL,
                notes TEXT,
                UNIQUE(user_id, repo_id)
            );
            """,
            "CREATE INDEX IF NOT EXISTS idx_turso_repos_cat ON repositories(category_id);",
            "CREATE INDEX IF NOT EXISTS idx_turso_repos_stars ON repositories(stars DESC);",
            "CREATE INDEX IF NOT EXISTS idx_turso_repos_lang ON repositories(language);",
            "CREATE INDEX IF NOT EXISTS idx_turso_repos_name ON repositories(name);",
            "CREATE INDEX IF NOT EXISTS idx_turso_snaps_repo ON snapshots(repo_id, timestamp);",
            "CREATE INDEX IF NOT EXISTS idx_turso_users_email ON users(email);",
            "CREATE INDEX IF NOT EXISTS idx_turso_user_wl ON user_watchlist(user_id, repo_id);",
            "CREATE INDEX IF NOT EXISTS idx_turso_sessions ON sessions(user_id);"
        ]
        return self.execute_batch(schema_sqls)
