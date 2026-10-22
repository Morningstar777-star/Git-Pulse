from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class MomentumFactors(BaseModel):
    velocity_score: float = Field(..., description="Normalized stars gained per day")
    acceleration_score: float = Field(..., description="Change in velocity over recent intervals")
    novelty_bonus: float = Field(..., description="Multiplier favoring recent repositories with breakout growth")
    scale_dampener: float = Field(..., description="Log-scale weight preventing massive repos from dominating solely on baseline volume")
    confidence: float = Field(..., description="Coverage penalty based on snapshot density and observation count")
    composite_momentum: float = Field(..., description="Final composite momentum index (0 - 100)")

class SparklinePoint(BaseModel):
    date: str
    stars: int

class RepositoryBase(BaseModel):
    id: int
    full_name: str
    name: str
    owner: str
    html_url: str
    description: Optional[str] = None
    language: Optional[str] = None
    topics: List[str] = []
    stars: int
    forks: int
    open_issues: int
    created_at: str
    pushed_at: Optional[str] = None
    category_id: str
    is_emerging: bool = False
    is_saved: bool = False
    momentum_score: float
    momentum_rank: Optional[int] = None
    recent_growth_24h: int = 0
    recent_growth_7d: int = 0
    recent_growth_30d: int = 0
    stars_per_day: int = 0
    growth_1d_pct: Optional[float] = None
    growth_7d_pct: Optional[float] = None
    growth_30d_pct: Optional[float] = None
    sparkline: List[int] = []
    momentum_factors: Optional[MomentumFactors] = None

class RepositoryDetail(RepositoryBase):
    snapshots: List[SparklinePoint] = []
    related_repositories: List[RepositoryBase] = []

class TopicItem(BaseModel):
    topic: str
    count: int

class TopicCategory(BaseModel):
    id: str
    name: str
    description: str
    repository_count: int
    total_stars: int
    emerging_count: int
    top_repositories: List[RepositoryBase] = []

class ModelBenchmarkResult(BaseModel):
    model_name: str
    ndcg_10: float
    precision_10: float
    spearman_corr: float
    mae: float
    description: str

class BenchmarkReport(BaseModel):
    active_model: str
    evaluated_at: str
    results: List[ModelBenchmarkResult]
    feature_importances: Dict[str, float] = {}
    methodology: str

class SystemStatus(BaseModel):
    last_refresh_at: Optional[str] = None
    next_refresh_at: Optional[str] = None
    total_repositories: int
    total_snapshots: int
    total_topics: int = 0
    github_token_configured: bool
    rate_limit_remaining: Optional[int] = None
    rate_limit_limit: Optional[int] = None
    active_algorithm: str
    is_refreshing: bool = False

class WatchlistRequest(BaseModel):
    repo_id: int
    notes: Optional[str] = None
