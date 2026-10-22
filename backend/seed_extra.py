import sys
import json
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from app.database import get_sync_connection
from app.seed_data import RAW_SEED_REPOSITORIES, generate_multi_day_snapshots
from datetime import datetime, timezone

conn = get_sync_connection()
cursor = conn.cursor()
now_iso = datetime.now(timezone.utc).isoformat()

added = 0
for repo in RAW_SEED_REPOSITORIES:
    cursor.execute("SELECT id FROM repositories WHERE full_name = ?", (repo["full_name"],))
    row = cursor.fetchone()
    if not row:
        cursor.execute("""
            INSERT INTO repositories (
                full_name, name, owner, html_url, description, language,
                topics, stars, forks, open_issues, created_at, pushed_at,
                category_id, is_emerging, last_crawled_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            repo["full_name"], repo["name"], repo["owner"],
            f"https://github.com/{repo['full_name']}", repo["description"], repo["language"],
            json.dumps(repo["topics"]), repo["stars"], repo["forks"], repo["open_issues"],
            repo["created_at"], now_iso, repo["category_id"], 1 if repo["is_emerging"] else 0, now_iso
        ))
        repo_id = cursor.lastrowid
        snaps = generate_multi_day_snapshots(repo_id, repo["stars"], repo["forks"], repo["growth_24h"], repo["growth_7d"], repo["growth_30d"])
        for s in snaps:
            cursor.execute("""
                INSERT INTO snapshots (
                    repo_id, timestamp, stars, forks, open_issues,
                    delta_stars_24h, delta_stars_7d, delta_stars_30d
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (s["repo_id"], s["timestamp"], s["stars"], s["forks"], s["open_issues"], s["delta_stars_24h"], s["delta_stars_7d"], s["delta_stars_30d"]))
        added += 1

conn.commit()
print(f"Successfully seeded extra repositories. Added: {added}")
