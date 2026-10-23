from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from app.database import get_db_connection
from app.models.schemas import RepositoryBase, WatchlistRequest
from app.routes.repositories import row_to_repo_dict
from app.auth import get_current_user_optional, get_current_user_required

router = APIRouter(prefix="/api/watchlist", tags=["Watchlist"])

@router.get("", response_model=List[RepositoryBase])
async def get_watchlist(
    user: Optional[dict] = Depends(get_current_user_optional),
    db = Depends(get_db_connection)
):
    """
    Fetch all repositories bookmarked in the personal watchlist.
    If unauthenticated, returns empty list (sign in required to view saved bookmarks).
    """
    if not user:
        return []

    cursor = await db.execute("""
        SELECT r.*, w.added_at as saved_at
        FROM repositories r
        JOIN user_watchlist w ON r.id = w.repo_id
        WHERE w.user_id = ?
        ORDER BY w.added_at DESC;
    """, (user["id"],))
    rows = await cursor.fetchall()

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
async def toggle_watchlist(
    req: WatchlistRequest,
    user: dict = Depends(get_current_user_required),
    db = Depends(get_db_connection)
):
    """
    Add or remove repository from user's personal watchlist.
    Requires authentication (returns 401 if unauthenticated).
    """
    cursor = await db.execute(
        "SELECT id FROM user_watchlist WHERE user_id = ? AND repo_id = ?;",
        (user["id"], req.repo_id)
    )
    row = await cursor.fetchone()

    if row:
        await db.execute(
            "DELETE FROM user_watchlist WHERE user_id = ? AND repo_id = ?;",
            (user["id"], req.repo_id)
        )
        await db.commit()
        return {"status": "REMOVED", "repo_id": req.repo_id, "is_saved": False}
    else:
        now_iso = datetime.now(timezone.utc).isoformat()
        await db.execute(
            "INSERT INTO user_watchlist (user_id, repo_id, added_at, notes) VALUES (?, ?, ?, ?);",
            (user["id"], req.repo_id, now_iso, req.notes)
        )
        await db.commit()
        return {"status": "SAVED", "repo_id": req.repo_id, "is_saved": True}

@router.delete("/{repo_id}", response_model=dict)
async def remove_from_watchlist(
    repo_id: int,
    user: dict = Depends(get_current_user_required),
    db = Depends(get_db_connection)
):
    """Remove repository from user's personal watchlist."""
    await db.execute(
        "DELETE FROM user_watchlist WHERE user_id = ? AND repo_id = ?;",
        (user["id"], repo_id)
    )
    await db.commit()
    return {"status": "REMOVED", "repo_id": repo_id, "is_saved": False}
