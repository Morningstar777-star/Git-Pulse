"""
Migration Script: Local SQLite -> Turso Cloud Database.
Pushes all existing 2,100+ repositories, snapshots, and schemas from local SQLite to Turso.
"""

import sys
import os
import sqlite3
import argparse
from pathlib import Path

# Add project root and backend to path
backend_dir = Path(__file__).resolve().parent.parent
project_root = backend_dir.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from app.turso_client import TursoClient
from app.config import DB_PATH, TURSO_DATABASE_URL, TURSO_AUTH_TOKEN

def run_migration(db_url: str, auth_token: str):
    print(f"[*] Initializing connection to Turso: {db_url}")
    client = TursoClient(db_url=db_url, auth_token=auth_token)

    # 1. Test Connection
    try:
        test_res = client.execute("SELECT 1 AS alive;")
        print(f"[+] Connection verified successfully: {test_res}")
    except Exception as e:
        print(f"[-] Failed to authenticate with Turso: {e}")
        return False

    # 2. Initialize Database Schema
    print("[*] Creating database tables and indexes on Turso...")
    try:
        client.init_schema()
        print("[+] All tables (repositories, snapshots, users, watchlist, sessions) initialized successfully.")
    except Exception as e:
        print(f"[-] Schema creation error: {e}")
        return False

    # 3. Read Local SQLite Database
    local_db = Path(DB_PATH)
    if not local_db.exists():
        print(f"[-] Local database not found at {local_db}")
        return False

    print(f"[*] Reading records from local database: {local_db}")
    conn = sqlite3.connect(str(local_db))
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Migrate Repositories
    cursor.execute("SELECT * FROM repositories;")
    repos = cursor.fetchall()
    print(f"[*] Found {len(repos)} repositories to migrate.")

    batch_size = 50
    inserted_repos = 0
    for i in range(0, len(repos), batch_size):
        chunk = repos[i:i+batch_size]
        statements = []
        for r in chunk:
            full_name = r["full_name"].replace("'", "''")
            name = (r["name"] or "").replace("'", "''")
            owner = (r["owner"] or "").replace("'", "''")
            html_url = (r["html_url"] or "").replace("'", "''")
            desc = (r["description"] or "").replace("'", "''")
            desc_en = (r["description_en"] or "").replace("'", "''")
            lang = (r["language"] or "").replace("'", "''")
            topics = (r["topics"] or "").replace("'", "''")
            cat_id = (r["category_id"] or "").replace("'", "''")
            created_at = (r["created_at"] or "").replace("'", "''")
            pushed_at = (r["pushed_at"] or "").replace("'", "''")
            last_crawled = (r["last_crawled_at"] or "").replace("'", "''")
            stars = r["stars"] or 0
            forks = r["forks"] or 0
            issues = r["open_issues"] or 0
            is_emerging = 1 if r["is_emerging"] else 0

            sql = f"""
            INSERT OR REPLACE INTO repositories 
            (id, full_name, name, owner, html_url, description, language, topics, stars, forks, open_issues, created_at, pushed_at, category_id, is_emerging, last_crawled_at, description_en)
            VALUES 
            ({r["id"]}, '{full_name}', '{name}', '{owner}', '{html_url}', '{desc}', '{lang}', '{topics}', {stars}, {forks}, {issues}, '{created_at}', '{pushed_at}', '{cat_id}', {is_emerging}, '{last_crawled}', '{desc_en}');
            """
            statements.append(sql.strip())
        try:
            client.execute_batch(statements)
            inserted_repos += len(chunk)
            print(f"    -> Synced {inserted_repos}/{len(repos)} repositories to Turso...")
        except Exception as e:
            print(f"    [-] Chunk sync error: {e}")

    # Migrate Snapshots
    cursor.execute("SELECT * FROM snapshots;")
    snaps = cursor.fetchall()
    print(f"[*] Found {len(snaps)} snapshots to migrate.")
    inserted_snaps = 0
    for i in range(0, len(snaps), batch_size):
        chunk = snaps[i:i+batch_size]
        statements = []
        for s in chunk:
            ts = (s["timestamp"] or "").replace("'", "''")
            sql = f"""
            INSERT OR REPLACE INTO snapshots
            (id, repo_id, timestamp, stars, forks, open_issues, delta_stars_24h, delta_stars_7d, delta_stars_30d)
            VALUES
            ({s["id"]}, {s["repo_id"]}, '{ts}', {s["stars"] or 0}, {s["forks"] or 0}, {s["open_issues"] or 0}, {s["delta_stars_24h"] or 0}, {s["delta_stars_7d"] or 0}, {s["delta_stars_30d"] or 0});
            """
            statements.append(sql.strip())
        try:
            client.execute_batch(statements)
            inserted_snaps += len(chunk)
        except Exception as e:
            print(f"    [-] Snapshot chunk error: {e}")
    print(f"[+] Synced {inserted_snaps} snapshots to Turso.")

    # 4. Remote Verification
    count_res = client.execute("SELECT COUNT(*) AS total FROM repositories;")
    remote_total = count_res[0]["total"] if count_res else 0
    print("\n" + "="*50)
    print(f"[SUCCESS] Turso Cloud Migration Complete!")
    print(f"Total Repositories on Turso: {remote_total}")
    print("="*50 + "\n")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Migrate local SQLite to Turso")
    parser.add_argument("--url", default="libsql://git-pulse-lucimorningstar.aws-ap-south-1.turso.io", help="Turso DB URL")
    parser.add_argument("--token", default="", help="Turso Auth Token (JWT)")
    args = parser.parse_args()

    token = args.token or TURSO_AUTH_TOKEN or os.getenv("TURSO_AUTH_TOKEN", "")
    if not token:
        print("\n[!] TURSO_AUTH_TOKEN is required to connect to Turso.")
        print("    Usage: python backend/scripts/migrate_to_turso.py --token <YOUR_TURSO_TOKEN>\n")
        print("    To get your token, either:")
        print("    1. Web Dashboard: https://turso.tech/app -> Database -> Generate Token")
        print("    2. CLI: turso db tokens create git-pulse-lucimorningstar\n")
        sys.exit(1)

    run_migration(args.url, token)
