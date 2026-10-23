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

    def execute_raw(self, sql: str, params: Optional[List[Any]] = None) -> 'TursoCursor':
        """Execute SQL statement and return a cursor with metadata and lastrowid."""
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
            return TursoCursor([])

        first_res = results[0]
        if first_res.get("type") == "error":
            err = first_res.get("error", {})
            raise Exception(f"Turso SQL Error: {err.get('message', 'Unknown error')}")

        resp_obj = first_res.get("response", {})
        result_obj = resp_obj.get("result", {})
        cols = [c.get("name") for c in result_obj.get("cols", [])]
        rows = result_obj.get("rows", [])
        last_insert_rowid = result_obj.get("last_insert_rowid")
        affected_row_count = result_obj.get("affected_row_count", 0)

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
        return TursoCursor(
            out,
            lastrowid=int(last_insert_rowid) if last_insert_rowid is not None else None,
            rowcount=affected_row_count
        )

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


class TursoRow:
    """Row wrapper that supports both dict-key and numeric-index access like sqlite3.Row."""
    def __init__(self, data: Dict[str, Any]):
        self._data = data
        self._keys = list(data.keys())
        self._values = list(data.values())

    def __getitem__(self, key_or_idx: Any) -> Any:
        if isinstance(key_or_idx, int):
            return self._values[key_or_idx]
        return self._data[key_or_idx]

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def keys(self) -> List[str]:
        return self._keys

    def values(self) -> List[Any]:
        return self._values

    def items(self):
        return self._data.items()

    def __iter__(self):
        return iter(self._data)

    def __contains__(self, key: str) -> bool:
        return key in self._data

    def __repr__(self) -> str:
        return f"<TursoRow {self._data}>"


class TursoCursor:
    """Async cursor wrapper providing fetchall(), fetchone(), and lastrowid."""
    def __init__(self, raw_rows: List[Dict[str, Any]], lastrowid: Optional[int] = None, rowcount: int = 0):
        self._raw_rows = raw_rows
        self._idx = 0
        self.lastrowid = lastrowid
        self.rowcount = rowcount

    async def fetchall(self) -> List[TursoRow]:
        return [TursoRow(r) for r in self._raw_rows]

    async def fetchone(self) -> Optional[TursoRow]:
        if self._idx < len(self._raw_rows):
            r = self._raw_rows[self._idx]
            self._idx += 1
            return TursoRow(r)
        return None

    def __iter__(self):
        return (TursoRow(r) for r in self._raw_rows)


class TursoConnection:
    """Async connection adapter for FastAPI matching aiosqlite interface."""
    def __init__(self, client: TursoClient):
        self.client = client

    async def execute(self, sql: str, params: Optional[Any] = None) -> TursoCursor:
        param_list = None
        if params is not None:
            if isinstance(params, (tuple, list)):
                param_list = list(params)
            else:
                param_list = [params]
        return self.client.execute_raw(sql, param_list)

    async def commit(self):
        pass

    async def close(self):
        pass

