import json
from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from app.database import get_db_connection
from app.models.schemas import TopicCategory, TopicItem
from app.seed_data import TOPICS_METADATA
from app.routes.repositories import list_repositories

router = APIRouter(prefix="/api/topics", tags=["Topics"])

@router.get("", response_model=List[TopicCategory])
async def get_topics_overview(
    mode: str = Query("momentum", pattern="^(momentum|popularity)$"),
    time_window: str = Query("7d", pattern="^(24h|7d|30d)$"),
    limit_per_topic: int = Query(30, ge=4, le=100),
    db=Depends(get_db_connection)
):
    """
    Returns high-level curated categories for top tabs, populated with
    repositories ordered by the selected mode (BKM momentum or Popularity stars)
    and selected time window (24h daily, 7d weekly, 30d monthly).
    """
    topics_out = []

    for topic_meta in TOPICS_METADATA:
        cat_id = topic_meta["id"]
        
        cursor = await db.execute("""
            SELECT 
                COUNT(*) as repo_count,
                COALESCE(SUM(stars), 0) as total_stars,
                COALESCE(SUM(CASE WHEN is_emerging = 1 THEN 1 ELSE 0 END), 0) as emerging_count
            FROM repositories
            WHERE category_id = ?;
        """, (cat_id,))
        row = await cursor.fetchone()

        top_repos = await list_repositories(
            mode=mode,
            time_window=time_window,
            category_id=cat_id,
            page=1,
            page_size=limit_per_topic,
            db=db
        )

        topics_out.append(TopicCategory(
            id=cat_id,
            name=topic_meta["name"],
            description=topic_meta["description"],
            repository_count=row["repo_count"],
            total_stars=row["total_stars"],
            emerging_count=row["emerging_count"],
            top_repositories=top_repos
        ))

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
