from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db_connection
from app.models.schemas import RepositoryBase, WatchlistRequest
from app.routes.repositories import row_to_repo_dict

router = APIRouter(prefix="/api/watchlist", tags=["Watchlist"])

@router.get("", response_model=List[RepositoryBase])
async def get_watchlist(db=Depends(get_db_connection)):
    """Fetch all repositories bookmarked in the local watchlist."""
    cursor = await db.execute("""
        SELECT r.*, w.added_at as saved_at
        FROM repositories r
        JOIN watchlist w ON r.id = w.repo_id
        ORDER BY w.added_at DESC;
    """)
    rows = await cursor.fetchall()
    
    # Fetch snapshots
    repo_ids = [r["id"] for r in rows]
    snapshots_by_repo = {}
    if repo_ids:
        placeholders = ",".join("?" for _ in repo_ids)
        snap_cursor = await db.execute(
            f"SELECT * FROM snapshots WHERE repo_id IN ({placeholders}) ORDER BY timestamp ASC;",
            repo_ids
        )
        snap_rows = await snap_cursor.fetchall()
        for sr in snap_rows:
            rid = sr["repo_id"]
            if rid not in snapshots_by_repo:
                snapshots_by_repo[rid] = []
            snapshots_by_repo[rid].append(sr)

    results = []
    for r in rows:
        snaps = snapshots_by_repo.get(r["id"], [])
        item = row_to_repo_dict(r, snapshots=snaps, is_saved=True)
        results.append(item)

    return results

@router.post("", response_model=dict)
async def toggle_watchlist(req: WatchlistRequest, db=Depends(get_db_connection)):
    """Add or remove repository from watchlist (toggle)."""
    cursor = await db.execute("SELECT id FROM watchlist WHERE repo_id = ?;", (req.repo_id,))
    row = await cursor.fetchone()

    if row:
        await db.execute("DELETE FROM watchlist WHERE repo_id = ?;", (req.repo_id,))
        await db.commit()
        return {"status": "REMOVED", "repo_id": req.repo_id, "is_saved": False}
    else:
        now_iso = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "INSERT INTO watchlist (repo_id, added_at, notes) VALUES (?, ?, ?);",
            (req.repo_id, now_iso, req.notes)
        )
        await db.commit()
        return {"status": "SAVED", "repo_id": req.repo_id, "is_saved": True}

@router.delete("/{repo_id}", response_model=dict)
async def remove_from_watchlist(repo_id: int, db=Depends(get_db_connection)):
    """Remove a repository from watchlist."""
    await db.execute("DELETE FROM watchlist WHERE repo_id = ?;", (repo_id,))
    await db.commit()
    return {"status": "REMOVED", "repo_id": repo_id, "is_saved": False}
