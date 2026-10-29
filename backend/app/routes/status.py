from fastapi import APIRouter, Depends, Body
from app.database import get_db_connection
from app.models.schemas import SystemStatus
from app.config import GITHUB_TOKEN
from app.github_client import github_client
from app.scheduler import scheduler

router = APIRouter(prefix="/api/status", tags=["Status"])

ACTIVE_ALGORITHM_STATE = "baseline"

@router.get("", response_model=SystemStatus)
async def get_system_status(db=Depends(get_db_connection)):
    """Fetch live system telemetry and crawler status."""
    cursor_repos = await db.execute("SELECT COUNT(*) FROM repositories;")
    total_repos = (await cursor_repos.fetchone())[0]

    cursor_snaps = await db.execute("SELECT COUNT(*) FROM snapshots;")
    total_snaps = (await cursor_snaps.fetchone())[0]

    # Calculate total unique topics
    cursor_topics = await db.execute("SELECT topics FROM repositories WHERE topics IS NOT NULL;")
    topic_rows = await cursor_topics.fetchall()
    all_topics = set()
    for tr in topic_rows:
        if tr[0]:
            try:
                import json
                items = json.loads(tr[0]) if tr[0].startswith("[") else tr[0].split(",")
                for it in items:
                    c = it.strip().lower()
                    if len(c) > 1:
                        all_topics.add(c)
            except Exception:
                pass
    total_topics = len(all_topics)

    # Fetch last crawl timestamp
    cursor_crawl = await db.execute(
        "SELECT finished_at FROM crawl_history WHERE LOWER(status) = 'completed' ORDER BY id DESC LIMIT 1;"
    )
    last_crawl = await cursor_crawl.fetchone()
    last_time = None
    if last_crawl and last_crawl[0]:
        last_time = last_crawl[0]
    else:
        cursor_latest = await db.execute("SELECT MAX(last_crawled_at) FROM repositories;")
        row_latest = await cursor_latest.fetchone()
        if row_latest and row_latest[0]:
            last_time = row_latest[0]
        else:
            last_time = scheduler.last_run_at

    return SystemStatus(
        last_refresh_at=last_time,
        next_refresh_at=scheduler.next_run_at,
        total_repositories=total_repos,
        total_snapshots=total_snaps,
        total_topics=total_topics,
        github_token_configured=bool(GITHUB_TOKEN),
        rate_limit_remaining=github_client.rate_limit_remaining,
        rate_limit_limit=github_client.rate_limit_limit,
        active_algorithm=ACTIVE_ALGORITHM_STATE,
        is_refreshing=github_client.is_running
    )

@router.post("/refresh", response_model=dict)
async def trigger_manual_refresh():
    """Manually initiate a GitHub trend sync."""
    if github_client.is_running:
        return {"status": "ALREADY_IN_PROGRESS", "message": "Crawler is already active."}
    
    # Run in background via scheduler trigger
    res = await scheduler.trigger_now()
    return res

@router.post("/algorithm", response_model=dict)
async def set_active_algorithm(payload: dict = Body(...)):
    """Switch active ranking algorithm ('baseline', 'gbdt', 'lstm')."""
    global ACTIVE_ALGORITHM_STATE
    algo = payload.get("algorithm", "baseline").lower()
    if algo in ["baseline", "probabilistic", "gbdt", "lstm"]:
        ACTIVE_ALGORITHM_STATE = algo
        return {"status": "UPDATED", "active_algorithm": ACTIVE_ALGORITHM_STATE}
    return {"status": "ERROR", "message": f"Unsupported algorithm '{algo}'"}
