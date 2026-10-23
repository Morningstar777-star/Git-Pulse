import time
import json
import math
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from app.database import get_db_connection
from app.auth import get_current_user_optional
from app.models.schemas import TopicCategory, TopicItem
from app.seed_data import TOPICS_METADATA
from app.routes.repositories import row_to_repo_dict

router = APIRouter(prefix="/api/topics", tags=["Topics"])

# In-memory TTL cache for high-speed response
_TOPICS_CACHE = {}
_TOPICS_CACHE_TIMESTAMP = {}
CACHE_TTL_SECONDS = 600  # 10 minutes cache for instant lightning responses

@router.get("", response_model=List[TopicCategory])
async def get_topics_overview(
    mode: str = Query("momentum", pattern="^(momentum|popularity)$"),
    time_window: str = Query("7d", pattern="^(24h|7d|30d)$"),
    limit_per_topic: int = Query(20, ge=4, le=60),
    user: Optional[dict] = Depends(get_current_user_optional),
    db=Depends(get_db_connection)
):
    """
    Returns high-level curated categories for top tabs, populated with
    repositories ordered by the selected mode (BKM momentum or Popularity stars)
    and selected time window (24h daily, 7d weekly, 30d monthly).
    Optimized with single-batch queries and in-memory caching.
    """
    user_id = user["id"] if user and isinstance(user, dict) else None
    cache_key = f"{mode}:{time_window}:{limit_per_topic}:{user_id}"
    now = time.time()

    if cache_key in _TOPICS_CACHE and (now - _TOPICS_CACHE_TIMESTAMP.get(cache_key, 0)) < CACHE_TTL_SECONDS:
        return _TOPICS_CACHE[cache_key]

    # 1. Fetch user watchlist IDs if signed in
    saved_ids = set()
    if user_id:
        try:
            saved_cursor = await db.execute("SELECT repo_id FROM user_watchlist WHERE user_id = ?;", (user_id,))
            saved_rows = await saved_cursor.fetchall()
            saved_ids = {r[0] for r in saved_rows}
        except Exception:
            pass

    # 2. Single high-speed GROUP BY query for all category stats
    stats_cursor = await db.execute("""
        SELECT 
            category_id,
            COUNT(*) as repo_count,
            COALESCE(SUM(stars), 0) as total_stars,
            COALESCE(SUM(CASE WHEN is_emerging = 1 THEN 1 ELSE 0 END), 0) as emerging_count
        FROM repositories
        GROUP BY category_id;
    """)
    stats_rows = await stats_cursor.fetchall()
    stats_by_cat = {r["category_id"]: r for r in stats_rows}

    # 3. Single query to fetch categorized repositories ordered for fast selection
    order_clause = "ORDER BY stars DESC" if mode == "popularity" else "ORDER BY is_emerging DESC, stars DESC"
    all_repos_cursor = await db.execute(f"SELECT * FROM repositories WHERE category_id IS NOT NULL {order_clause};")
    all_repos_rows = await all_repos_cursor.fetchall()

    # Group candidate repos by category (exact limit needed)
    candidate_repos_by_cat = {}
    selected_repo_ids = []
    fetch_buffer = limit_per_topic + (0 if mode == "popularity" else 5)

    for r in all_repos_rows:
        cid = r["category_id"]
        if cid not in candidate_repos_by_cat:
            candidate_repos_by_cat[cid] = []
        if len(candidate_repos_by_cat[cid]) < fetch_buffer:
            candidate_repos_by_cat[cid].append(r)
            selected_repo_ids.append(r["id"])

    # 4. Streamlined batch query for snapshots of candidate repositories
    snapshots_by_repo = {}
    if selected_repo_ids:
        placeholders = ",".join("?" for _ in selected_repo_ids)
        snap_cursor = await db.execute(
            f"SELECT repo_id, stars, delta_stars_24h, delta_stars_7d, delta_stars_30d FROM snapshots WHERE repo_id IN ({placeholders}) ORDER BY timestamp ASC;",
            selected_repo_ids
        )
        snap_rows = await snap_cursor.fetchall()
        for sr in snap_rows:
            rid = sr["repo_id"]
            if rid not in snapshots_by_repo:
                snapshots_by_repo[rid] = []
            snapshots_by_repo[rid].append(sr)

    # 5. Enrich and sort repositories per category
    topics_out = []
    for topic_meta in TOPICS_METADATA:
        cat_id = topic_meta["id"]
        stats = stats_by_cat.get(cat_id, {})
        raw_candidates = candidate_repos_by_cat.get(cat_id, [])

        cat_items = []
        for r in raw_candidates:
            snaps = snapshots_by_repo.get(r["id"], [])
            is_saved = r["id"] in saved_ids
            item = row_to_repo_dict(r, snapshots=snaps, is_saved=is_saved)
            cat_items.append(item)

        # Sort based on mode
        if mode == "popularity":
            cat_items.sort(key=lambda x: x["stars"], reverse=True)
        else:
            cat_items.sort(key=lambda x: (x.get("is_emerging", False), x["momentum_score"], x["growth_7d_pct"]), reverse=True)

        top_repos = cat_items[:limit_per_topic]

        topics_out.append(TopicCategory(
            id=cat_id,
            name=topic_meta["name"],
            description=topic_meta["description"],
            repository_count=stats.get("repo_count", len(cat_items)),
            total_stars=stats.get("total_stars", sum(x["stars"] for x in cat_items)),
            emerging_count=stats.get("emerging_count", sum(1 for x in cat_items if x.get("is_emerging"))),
            top_repositories=top_repos
        ))

    # Save to in-memory cache
    _TOPICS_CACHE[cache_key] = topics_out
    _TOPICS_CACHE_TIMESTAMP[cache_key] = now

    return topics_out

@router.get("/all", response_model=List[TopicItem])
async def get_all_topics(
    q: Optional[str] = None,
    limit: int = Query(1000, ge=1, le=2000),
    db=Depends(get_db_connection)
):
    """
    Dynamically extracts, aggregates, and ranks ALL unique GitHub topics
    across all tracked repositories in SQLite (supports 900+ topics).
    """
    cursor = await db.execute("SELECT topics FROM repositories WHERE topics IS NOT NULL;")
    rows = await cursor.fetchall()

    topic_counts = {}
    for r in rows:
        raw = r[0]
        if not raw:
            continue
        try:
            parsed = json.loads(raw) if raw.startswith("[") else [t.strip() for t in raw.split(",")]
            for t in parsed:
                cleaned = t.strip().lower()
                if cleaned and len(cleaned) > 1:
                    topic_counts[cleaned] = topic_counts.get(cleaned, 0) + 1
        except Exception:
            pass

    # Filter by query if provided
    items = []
    for topic, count in topic_counts.items():
        if q and q.lower() not in topic:
            continue
        items.append(TopicItem(topic=topic, count=count))

    # Sort descending by repository count
    items.sort(key=lambda x: (x.count, x.topic), reverse=True)
    return items[:limit]
