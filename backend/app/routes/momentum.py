import json
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException
from app.database import get_db_connection
from app.models.schemas import RepositoryBase, BenchmarkReport, ModelBenchmarkResult
from app.routes.repositories import list_repositories
from app.models.evaluate import run_experiment_evaluation

router = APIRouter(prefix="/api/momentum", tags=["Momentum Engine"])

# In-memory cached benchmark report
CACHED_BENCHMARK: Dict[str, Any] = {}

@router.get("/radar", response_model=List[RepositoryBase])
async def get_momentum_radar(
    time_window: str = Query("7d", regex="^(24h|7d|30d)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(30, ge=5, le=300),
    db=Depends(get_db_connection)
):
    """
    Supplies the persistent right-side Momentum Radar with ranked repositories,
    daily velocity metrics, and infinite scroll pagination.
    """
    items = await list_repositories(
        mode="momentum",
        time_window=time_window,
        page=page,
        page_size=limit,
        db=db
    )
    return items

@router.get("/benchmark", response_model=BenchmarkReport)
async def get_momentum_benchmark(db=Depends(get_db_connection)):
    """
    Returns the comparative ML experiment results:
    Calibrated Baseline Formula vs Hist-GBDT vs Sequential LSTM.
    """
    global CACHED_BENCHMARK
    if CACHED_BENCHMARK:
        return BenchmarkReport(**CACHED_BENCHMARK)

    # If not yet cached, generate evaluation from SQLite repository data
    cursor = await db.execute("SELECT * FROM repositories;")
    rows = await cursor.fetchall()
    
    # Fetch snapshots
    snap_cursor = await db.execute("SELECT * FROM snapshots ORDER BY timestamp ASC;")
    all_snaps = await snap_cursor.fetchall()
    snaps_map = {}
    for s in all_snaps:
        rid = s["repo_id"]
        if rid not in snaps_map:
            snaps_map[rid] = []
        snaps_map[rid].append(s)

    repos_payload = []
    for r in rows:
        snaps = snaps_map.get(r["id"], [])
        g24 = int(snaps[-1]["delta_stars_24h"]) if snaps else max(1, int(r["stars"] * 0.005))
        g7 = int(snaps[-1]["delta_stars_7d"]) if snaps else max(5, int(r["stars"] * 0.025))
        g30 = int(snaps[-1]["delta_stars_30d"]) if snaps else max(20, int(r["stars"] * 0.08))
        
        repos_payload.append({
            "id": r["id"],
            "full_name": r["full_name"],
            "stars": r["stars"],
            "forks": r["forks"],
            "open_issues": r["open_issues"],
            "created_at": r["created_at"],
            "recent_growth_24h": g24,
            "recent_growth_7d": g7,
            "recent_growth_30d": g30,
            "snapshot_count": len(snaps)
        })

    eval_result = run_experiment_evaluation(repos_payload)
    CACHED_BENCHMARK = eval_result
    return BenchmarkReport(**eval_result)

@router.post("/benchmark/run", response_model=BenchmarkReport)
async def rerun_benchmark(db=Depends(get_db_connection)):
    """Force re-run the benchmark suite across current repository snapshots."""
    global CACHED_BENCHMARK
    CACHED_BENCHMARK = {}
    return await get_momentum_benchmark(db=db)
