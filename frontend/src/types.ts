export interface MomentumFactors {
  velocity_score: number;
  acceleration_score: number;
  novelty_bonus: number;
  scale_dampener: number;
  confidence: number;
  composite_momentum: number;
}

export interface SparklinePoint {
  date: string;
  stars: number;
}

export interface Repository {
  id: number;
  full_name: string;
  name: string;
  owner: string;
  html_url: string;
  description: string | null;
  description_en?: string | null;
  language: string | null;
  topics: string[];
  stars: number;
  forks: number;
  open_issues: number;
  created_at: string;
  pushed_at: string | null;
  category_id: string;
  is_emerging: boolean;
  is_saved: boolean;
  momentum_score: number;
  momentum_rank: number | null;
  recent_growth_24h: number;
  recent_growth_7d: number;
  recent_growth_30d: number;
  stars_per_day: number;
  growth_1d_pct?: number | null;
  growth_7d_pct?: number | null;
  growth_30d_pct?: number | null;
  sparkline: number[];
  momentum_factors?: MomentumFactors;
}

export interface RepositoryDetail extends Repository {
  snapshots: SparklinePoint[];
  related_repositories: Repository[];
}

export interface TopicItem {
  topic: string;
  count: number;
}

export interface TopicCategory {
  id: string;
  name: string;
  description: string;
  repository_count: number;
  total_stars: number;
  emerging_count: number;
  top_repositories: Repository[];
}

export interface SystemStatus {
  last_refresh_at: string | null;
  next_refresh_at: string | null;
  total_repositories: number;
  total_snapshots: number;
  total_topics: number;
  github_token_configured: boolean;
  rate_limit_remaining: number | null;
  rate_limit_limit: number | null;
  active_algorithm: string;
  is_refreshing: boolean;
}

export type SortMode = 'momentum' | 'popularity';
export type TimeWindow = '24h' | '7d' | '30d';
export type PopularitySortBy = 'stars' | 'forks';
