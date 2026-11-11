import math
import json
import re
import time
import sqlite3
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from app.config import DB_PATH
from app.database import get_db_connection
from app.models.schemas import RepositoryBase, RepositoryDetail, SparklinePoint, MomentumFactors
from app.models.smart_momentum import calculate_smart_momentum
from app.github_client import github_client
from app.search_engine import parse_search_intent, score_repository_relevance
from app.translator import translate_cjk_sync
from app.auth import get_current_user_optional

router = APIRouter(prefix="/api/repositories", tags=["Repositories"])

_REPOS_CACHE = {}
_REPOS_CACHE_TIMESTAMP = {}
CACHE_TTL = 120  # 2 minutes in-memory cache for snappy switching without stale data

def clear_repositories_cache() -> None:
    _REPOS_CACHE.clear()
    _REPOS_CACHE_TIMESTAMP.clear()

def build_momentum_candidate_cte(time_window: str = "7d"):
    """
    Build indexed recent-snapshot CTE and freshness-weighted velocity SQL ORDER BY clause
    so smaller breakout repos aren't starved out by legacy cumulative-star giants.
    """
    cte_sql = """
        WITH recent_snaps AS (
            SELECT repo_id, delta_stars_24h, delta_stars_7d, delta_stars_30d, timestamp,
                   ROW_NUMBER() OVER (PARTITION BY repo_id ORDER BY timestamp DESC) AS srn
            FROM snapshots
            WHERE timestamp >= strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-30 days')
        ),
        latest_vel AS (
            SELECT repo_id, delta_stars_24h, delta_stars_7d, delta_stars_30d, timestamp
            FROM recent_snaps
            WHERE srn = 1
        )
    """
    if time_window == "24h":
        vel_expr = "COALESCE(lv.delta_stars_24h, 0) * 1.0"
    elif time_window == "30d":
        vel_expr = "COALESCE(lv.delta_stars_30d, 0) / 30.0"
    else:
        vel_expr = "COALESCE(lv.delta_stars_7d, 0) / 7.0"

    age_days_expr = "MAX(0.0, julianday('now') - julianday(substr(COALESCE(lv.timestamp, r.last_crawled_at, '2020-01-01'), 1, 19)))"
    decay_expr = (
        f"CASE WHEN {age_days_expr} <= 2.5 THEN 1.0 "
        f"WHEN {age_days_expr} <= 5.0 THEN 0.45 "
        f"WHEN {age_days_expr} <= 10.0 THEN 0.15 "
        f"ELSE 0.03 END"
    )
    novelty_expr = (
        "CASE WHEN r.created_at >= strftime('%Y-%m-%dT%H:%M:%SZ', 'now', '-60 days') THEN 1.5 "
        "WHEN r.is_emerging = 1 THEN 1.25 ELSE 1.0 END"
    )
    order_expr = (
        f"(({vel_expr} * ({decay_expr}) * ({novelty_expr})) / (400.0 + r.stars * 0.03)) DESC, "
        "r.last_crawled_at DESC, r.stars DESC"
    )
    return cte_sql, order_expr

def momentum_sort_key(item: dict, time_window: str = "7d") -> tuple:
    """Rank repositories by calibrated BKM momentum blended with the active timeframe surge."""
    if time_window == "24h":
        tw_delta = item.get("recent_growth_24h", 0)
        tw_pct = item.get("growth_1d_pct") or 0.0
    elif time_window == "30d":
        tw_delta = item.get("recent_growth_30d", 0)
        tw_pct = item.get("growth_30d_pct") or 0.0
    else:
        tw_delta = item.get("recent_growth_7d", 0)
        tw_pct = item.get("growth_7d_pct") or 0.0

    m_score = item.get("momentum_score", 0.0)
    window_boost = math.log10(1.0 + max(0.0, float(tw_delta))) * 4.0 + min(15.0, math.log1p(max(0.0, float(tw_pct))) * 3.0)
    blended = round(m_score * 0.85 + window_boost, 3)
    return (blended, m_score, tw_delta)

def _calc_freshness_decay(snap_or_row) -> float:
    """Decay stale snapshot velocity smoothly if not observed in recent crawls (>2.5d)."""
    ts_str = None
    try:
        ts_str = snap_or_row["timestamp"]
    except Exception:
        try:
            ts_str = snap_or_row["last_crawled_at"]
        except Exception:
            ts_str = None
    if not ts_str:
        return 1.0
    try:
        from datetime import datetime, timezone
        dt = datetime.fromisoformat(str(ts_str).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        age_days = max(0.0, (datetime.now(timezone.utc) - dt).total_seconds() / 86400.0)
        if age_days <= 2.5:
            return 1.0
        return max(0.02, 0.5 ** ((age_days - 2.5) / 2.0))
    except Exception:
        return 1.0

def row_to_repo_dict(row, snapshots=None, is_saved=False) -> dict:
    topics = []
    if row["topics"]:
        try:
            topics = json.loads(row["topics"])
        except Exception:
            topics = [t.strip() for t in row["topics"].split(",") if t.strip()]

    # Extract growth from snapshots (applying freshness decay if stale) or conservative fallback
    recent_24h = 0
    recent_7d = 0
    recent_30d = 0
    sparkline = []

    if snapshots:
        latest = snapshots[-1]
        decay = _calc_freshness_decay(latest)
        recent_24h = int(float(latest["delta_stars_24h"] or 0) * decay)
        recent_7d = max(recent_24h, int(float(latest["delta_stars_7d"] or 0) * min(1.0, decay * 1.4)))
        recent_30d = max(recent_7d, int(float(latest["delta_stars_30d"] or 0) * min(1.0, decay * 1.8)))
        sparkline = [int(s["stars"]) for s in snapshots]
    else:
        stars_val = max(1, row["stars"])
        decay = _calc_freshness_decay(row)
        if decay >= 0.8:
            recent_24h = min(25, max(1, int(stars_val * 0.001)))
            recent_7d = min(150, max(3, int(stars_val * 0.005)))
            recent_30d = min(500, max(10, int(stars_val * 0.015)))
        else:
            recent_24h = 0
            recent_7d = 0
            recent_30d = 0
        sparkline = [int(stars_val * 0.96), int(stars_val * 0.98), int(stars_val * 0.99), stars_val]

    stars = max(1, row["stars"])
    # 1D percentage (growth relative to prior stars)
    prior_1d = max(10.0, float(stars - recent_24h))
    growth_1d_pct = round(min(500.0, (recent_24h / prior_1d) * 100.0), 1) if recent_24h > 0 else 0.0

    # 7D percentage
    prior_7d = max(10.0, float(stars - recent_7d))
    growth_7d_pct = round(min(1000.0, (recent_7d / prior_7d) * 100.0), 1) if recent_7d > 0 else 0.0

    # 30D percentage
    prior_30d = max(10.0, float(stars - recent_30d))
    growth_30d_pct = round(min(2000.0, (recent_30d / prior_30d) * 100.0), 1) if recent_30d > 0 else None

    # Stars per day
    stars_per_day = int(recent_24h if recent_24h > 0 else max(1, recent_7d // 7))

    # Calculate momentum factors using the smart BKM engine
    factors_raw = calculate_smart_momentum(
        stars=row["stars"],
        forks=row["forks"],
        open_issues=row["open_issues"],
        created_at_str=row["created_at"],
        recent_growth_24h=recent_24h,
        recent_growth_7d=recent_7d,
        recent_growth_30d=recent_30d,
        snapshot_count=len(snapshots) if snapshots else 3
    )

    factors = MomentumFactors(
        velocity_score=factors_raw["velocity_score"],
        acceleration_score=factors_raw["acceleration_score"],
        novelty_bonus=factors_raw["novelty_bonus"],
        scale_dampener=factors_raw["scale_dampener"],
        confidence=factors_raw["confidence"],
        composite_momentum=factors_raw["composite_momentum"]
    )

    desc_en = None
    try:
        desc_en = row["description_en"]
    except Exception:
        pass

    return {
        "id": row["id"],
        "full_name": row["full_name"],
        "name": row["name"],
        "owner": row["owner"],
        "html_url": row["html_url"],
        "description": row["description"],
        "description_en": desc_en,
        "language": row["language"],
        "topics": topics,
        "stars": row["stars"],
        "forks": row["forks"],
        "open_issues": row["open_issues"],
        "created_at": row["created_at"],
        "pushed_at": row["pushed_at"],
        "category_id": row["category_id"],
        "is_emerging": bool(row["is_emerging"]),
        "is_saved": is_saved,
        "momentum_score": factors.composite_momentum,
        "momentum_rank": None,
        "recent_growth_24h": recent_24h,
        "recent_growth_7d": recent_7d,
        "recent_growth_30d": recent_30d,
        "stars_per_day": stars_per_day,
        "growth_1d_pct": growth_1d_pct,
        "growth_7d_pct": growth_7d_pct,
        "growth_30d_pct": growth_30d_pct,
        "sparkline": sparkline,
        "momentum_factors": factors
    }

SEMANTIC_EXPANSIONS = {
    "speech": ["speech", "text-to-speech", "speech-to-text", "tts", "asr", "whisper", "voice", "speech-synthesis", "voice-cloning"],
    "voice": ["voice", "tts", "speech", "text-to-speech", "voice-cloning", "whisper", "audio"],
    "tts": ["tts", "text-to-speech", "speech", "speech-synthesis", "voice"],
    "stt": ["stt", "speech-to-text", "whisper", "asr", "transcription"],
    "whisper": ["whisper", "speech", "transcription", "asr", "audio"],
    "audio": ["audio", "sound", "music", "dsp", "voice", "speech"],
    "agent": ["agent", "agents", "llm-agent", "autonomous-agents", "crewai", "langchain", "mcp"],
    "agents": ["agent", "agents", "llm-agent", "autonomous-agents", "crewai", "langchain", "mcp"],
    "rag": ["rag", "retrieval", "vector", "embedding", "langchain", "llamaindex"],
    "diffusion": ["diffusion", "stable-diffusion", "comfyui", "image-generation", "flux"],
    "vision": ["computer-vision", "yolo", "segmentation", "object-detection", "opencv"],
    "quant": ["quantitative-finance", "trading", "algorithmic-trading", "crypto", "backtest"],
    "trading": ["trading", "algorithmic-trading", "quantitative-finance", "crypto", "backtesting"],
    "terminal": ["terminal", "cli", "tui", "shell", "bash", "zsh", "command-line"],
    "security": ["security", "cybersecurity", "pentest", "vulnerability", "exploit", "reverse-engineering"],
}

@router.get("", response_model=List[RepositoryBase])
async def list_repositories(
    mode: str = Query("momentum", pattern="^(momentum|popularity)$"),
    sort_by: str = Query("default"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    time_window: str = Query("7d", pattern="^(24h|7d|30d)$"),
    category_id: Optional[str] = None,
    topic: Optional[str] = None,
    language: Optional[str] = None,
    search: Optional[str] = None,
    q: Optional[str] = None,
    min_stars: Optional[int] = None,
    is_emerging: Optional[bool] = None,
    watchlist_only: bool = False,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    user: Optional[dict] = Depends(get_current_user_optional),
    db=Depends(get_db_connection)
):
    """
    List repositories supporting both 'Momentum' and 'Popularity' sorting modes,
    table column header sorting (1D, 7D, 30D, Stars, Per Day), topic tag filtering,
    language tags, live on-demand GitHub search, and infinite-scroll pagination.
    """
    user_id = user["id"] if user and isinstance(user, dict) else None
    cache_key = f"{mode}:{sort_by}:{sort_order}:{time_window}:{category_id}:{topic}:{language}:{search}:{q}:{min_stars}:{is_emerging}:{watchlist_only}:{page}:{page_size}:{user_id}"
    now_ts = time.time()
    if cache_key in _REPOS_CACHE and (now_ts - _REPOS_CACHE_TIMESTAMP.get(cache_key, 0)) < CACHE_TTL:
        return _REPOS_CACHE[cache_key]

    # Fetch watchlist repo IDs for authenticated user (empty if unauthenticated)
    saved_ids = set()
    if user and isinstance(user, dict):
        saved_cursor = await db.execute("SELECT repo_id FROM user_watchlist WHERE user_id = ?;", (user["id"],))
        saved_rows = await saved_cursor.fetchall()
        saved_ids = {r[0] for r in saved_rows}

    # Base query
    where_clauses = ["1=1"]
    params = []

    if category_id:
        where_clauses.append("category_id = ?")
        params.append(category_id)

    if topic:
        where_clauses.append("(LOWER(topics) LIKE ?)")
        params.append(f"%{topic.lower()}%")

    if language:
        where_clauses.append("LOWER(language) = LOWER(?)")
        params.append(language)

    if min_stars is not None:
        where_clauses.append("stars >= ?")
        params.append(min_stars)

    if is_emerging is not None:
        where_clauses.append("is_emerging = ?")
        params.append(1 if is_emerging else 0)

    intent = None
    effective_search = (search or q or "").strip()
    if effective_search:
        intent = parse_search_intent(effective_search)
        
        # Candidate SQL filtering: match meaningful keywords or concept terms
        candidate_terms = intent["meaningful_keywords"] + intent["expanded_terms"][:15]
        seen_t = set()
        unique_candidate_terms = []
        for t in candidate_terms:
            if t not in seen_t:
                seen_t.add(t)
                unique_candidate_terms.append(t)

        clause_parts = []
        for term in unique_candidate_terms:
            term_like = f"%{term}%"
            clause_parts.append("(LOWER(name) LIKE ? OR LOWER(full_name) LIKE ? OR LOWER(description) LIKE ? OR LOWER(description_en) LIKE ? OR LOWER(topics) LIKE ?)")
            params.extend([term_like, term_like, term_like, term_like, term_like])

        if "/" in intent["clean_query"]:
            clause_parts.append("LOWER(full_name) LIKE ?")
            params.append(f"%{intent['clean_query'].lower()}%")

        if clause_parts:
            where_clauses.append("(" + " OR ".join(clause_parts) + ")")
        query = f"SELECT * FROM repositories WHERE {' AND '.join(where_clauses)} LIMIT 150"
    elif mode == "popularity" or sort_by in ("stars", "stars_count", "forks", "forks_count"):
        order_col = "forks DESC" if sort_by in ("forks", "forks_count") else "stars DESC"
        query = f"SELECT * FROM repositories WHERE {' AND '.join(where_clauses)} ORDER BY {order_col} LIMIT 250"
    else:
        cte_sql, momentum_order = build_momentum_candidate_cte(time_window)
        query = (
            f"{cte_sql} "
            f"SELECT r.* FROM repositories r "
            f"LEFT JOIN latest_vel lv ON r.id = lv.repo_id "
            f"WHERE {' AND '.join(where_clauses)} "
            f"ORDER BY {momentum_order} LIMIT 250"
        )

    cursor = await db.execute(query, params)
    rows = await cursor.fetchall()

    # If search was given and returned few results (< 8), fetch dynamically from GitHub API using smart concept query
    if intent and (len(rows) < 8 or "/" in intent["clean_query"]):
        if "/" in intent["clean_query"] and len(intent["clean_query"].split("/")) == 2:
            await github_client.fetch_and_persist_repo_on_demand(intent["clean_query"])
        elif intent["github_query"]:
            await github_client.search_and_persist_topic_or_query(intent["github_query"], limit=20)
        
        # Re-query SQLite after dynamic fetch
        cursor = await db.execute(query, params)
        rows = await cursor.fetchall()

    # Pre-fetch snapshots for repos in result
    repo_ids = [r["id"] for r in rows]
    snapshots_by_repo = {}
    if repo_ids:
        placeholders = ",".join("?" for _ in repo_ids)
        snap_query = f"SELECT * FROM snapshots WHERE repo_id IN ({placeholders}) ORDER BY timestamp ASC;"
        snap_cursor = await db.execute(snap_query, repo_ids)
        snap_rows = await snap_cursor.fetchall()
        for sr in snap_rows:
            rid = sr["repo_id"]
            if rid not in snapshots_by_repo:
                snapshots_by_repo[rid] = []
            snapshots_by_repo[rid].append(sr)

    # Convert to enriched repository objects
    items = []
    for r in rows:
        if watchlist_only and r["id"] not in saved_ids:
            continue
        snaps = snapshots_by_repo.get(r["id"], [])
        is_saved = r["id"] in saved_ids
        item = row_to_repo_dict(r, snapshots=snaps, is_saved=is_saved)
        items.append(item)

    is_desc = (sort_order == "desc")

    # Priority 1: When user is actively searching, Semantic Intent Relevance is ALWAYS paramount
    if intent:
        # Score each item with smart semantic relevance
        for it in items:
            it["_relevance_score"] = score_repository_relevance(it, intent)

        # Filter out items with 0 relevance (strict intent matching)
        items = [it for it in items if it.get("_relevance_score", 0) > 0]

        if sort_by in ("stars", "stars_count"):
            items.sort(key=lambda x: (x.get("_relevance_score", 0), x["stars"]), reverse=True)
        elif sort_by in ("forks", "forks_count"):
            items.sort(key=lambda x: (x.get("_relevance_score", 0), x["forks"]), reverse=True)
        elif mode == "popularity":
            items.sort(key=lambda x: (x.get("_relevance_score", 0), x["stars"]), reverse=True)
        else:
            items.sort(key=lambda x: (x.get("_relevance_score", 0), x.get("momentum_score", 0), x.get("growth_7d_pct", 0)), reverse=True)

    # Priority 2: Custom Column / Header Sorting (when not searching)
    elif sort_by in ("stars", "stars_count"):
        items.sort(key=lambda x: x["stars"], reverse=is_desc)
    elif sort_by in ("forks", "forks_count"):
        items.sort(key=lambda x: x["forks"], reverse=is_desc)
    elif sort_by in ("1d", "growth_1d", "1d_pct"):
        items.sort(key=lambda x: x["growth_1d_pct"], reverse=is_desc)
    elif sort_by in ("7d", "growth_7d", "7d_pct"):
        items.sort(key=lambda x: x["growth_7d_pct"], reverse=is_desc)
    elif sort_by in ("30d", "growth_30d", "30d_pct"):
        items.sort(key=lambda x: (x.get("growth_30d_pct") or 0.0), reverse=is_desc)
    elif sort_by in ("per_day", "rate", "stars_per_day"):
        items.sort(key=lambda x: x["stars_per_day"], reverse=is_desc)
    elif sort_by in ("momentum", "momentum_score"):
        items.sort(key=lambda x: x["momentum_score"], reverse=is_desc)
    elif sort_by in ("repository", "name"):
        items.sort(key=lambda x: x["name"].lower(), reverse=is_desc)
    else:
        # Default Mode Sorting (when not searching)
            if mode == "popularity":
                # Surface high-star breakout projects with active velocity (like rea, NOT stale +1/day dinosaurs like tensorflow)
                def calc_popularity_score(x):
                    stars = max(10, x.get("stars", 0))
                    spd = max(1, x.get("stars_per_day", 0))
                    # Stale penalty if repo gains < 5 stars/day despite massive historical baseline
                    stale_factor = 0.2 if spd <= 2 else (0.5 if spd < 10 else 1.0)
                    return (math.log10(stars) * 12.0 + math.log10(spd) * 16.0 + (x.get("momentum_score", 0.0) * 0.1)) * stale_factor

                items.sort(key=calc_popularity_score, reverse=True)
            else:
                # Bayesian Kinetic Momentum (BKM) Engine: timeframe-responsive velocity & calibrated surge
                items.sort(key=lambda x: momentum_sort_key(x, time_window), reverse=True)

    # Assign momentum rank
    for idx, item in enumerate(items):
        item["momentum_rank"] = idx + 1

    # Pagination for infinite scroll
    start = (page - 1) * page_size
    end = start + page_size
    res = items[start:end]
    _REPOS_CACHE[cache_key] = res
    _REPOS_CACHE_TIMESTAMP[cache_key] = now_ts
    return res

@router.get("/{repo_id}", response_model=RepositoryDetail)
async def get_repository_detail(
    repo_id: int,
    user: Optional[dict] = Depends(get_current_user_optional),
    db=Depends(get_db_connection)
):
    """Fetch full repository details with chronological snapshots and related tools."""
    cursor = await db.execute("SELECT * FROM repositories WHERE id = ?;", (repo_id,))
    row = await cursor.fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Repository not found.")

    # Check watchlist for authenticated user
    is_saved = False
    if user and isinstance(user, dict):
        saved_cursor = await db.execute(
            "SELECT 1 FROM user_watchlist WHERE user_id = ? AND repo_id = ?;",
            (user["id"], repo_id)
        )
        is_saved = bool(await saved_cursor.fetchone())

    # Snapshots
    snap_cursor = await db.execute("SELECT * FROM snapshots WHERE repo_id = ? ORDER BY timestamp ASC;", (repo_id,))
    snap_rows = await snap_cursor.fetchall()
    
    base_dict = row_to_repo_dict(row, snapshots=snap_rows, is_saved=is_saved)

    # Deduplicate snapshot points by calendar date (keep latest per date)
    snaps_by_date = {}
    for sr in snap_rows:
        date_str = sr["timestamp"][:10]
        snaps_by_date[date_str] = SparklinePoint(date=date_str, stars=int(sr["stars"]))
    
    sorted_dates = sorted(snaps_by_date.keys())
    snapshot_points = [snaps_by_date[d] for d in sorted_dates[-14:]]

    # Fetch 4 related repositories in same category
    rel_cursor = await db.execute(
        "SELECT * FROM repositories WHERE category_id = ? AND id != ? ORDER BY stars DESC LIMIT 4;",
        (row["category_id"], repo_id)
    )
    rel_rows = await rel_cursor.fetchall()
    related = [row_to_repo_dict(r) for r in rel_rows]

    # If category has fewer than 4 repos, supplement with top breakout repos
    if len(related) < 4:
        needed = 4 - len(related)
        exclude_ids = [repo_id] + [r["id"] for r in related]
        placeholders = ",".join("?" for _ in exclude_ids)
        fb_cursor = await db.execute(
            f"SELECT * FROM repositories WHERE id NOT IN ({placeholders}) ORDER BY stars DESC LIMIT ?;",
            exclude_ids + [needed]
        )
        fb_rows = await fb_cursor.fetchall()
        related.extend([row_to_repo_dict(r) for r in fb_rows])

    return RepositoryDetail(
        **base_dict,
        snapshots=snapshot_points,
        related_repositories=related
    )
