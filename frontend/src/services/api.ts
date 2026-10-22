import { 
  Repository, 
  RepositoryDetail, 
  TopicCategory, 
  TopicItem, 
  SystemStatus, 
  SortMode, 
  TimeWindow, 
  PopularitySortBy 
} from '../types';

const API_BASE = '/api';

export async function fetchRepositories(params: {
  mode?: SortMode;
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
  time_window?: TimeWindow;
  category_id?: string;
  topic?: string;
  language?: string;
  search?: string;
  watchlist_only?: boolean;
  page?: number;
  page_size?: number;
}): Promise<Repository[]> {
  const query = new URLSearchParams();
  if (params.mode) query.set('mode', params.mode);
  if (params.sort_by) query.set('sort_by', params.sort_by);
  if (params.sort_order) query.set('sort_order', params.sort_order);
  if (params.time_window) query.set('time_window', params.time_window);
  if (params.category_id) query.set('category_id', params.category_id);
  if (params.topic) query.set('topic', params.topic);
  if (params.language) query.set('language', params.language);
  if (params.search) query.set('search', params.search);
  if (params.watchlist_only) query.set('watchlist_only', 'true');
  if (params.page) query.set('page', params.page.toString());
  if (params.page_size) query.set('page_size', params.page_size.toString());

  const res = await fetch(`${API_BASE}/repositories?${query.toString()}`);
  if (!res.ok) throw new Error(`Failed to fetch repositories (${res.status})`);
  return res.json();
}

export async function fetchRepositoryDetail(id: number): Promise<RepositoryDetail> {
  const res = await fetch(`${API_BASE}/repositories/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch repository #${id}`);
  return res.json();
}

export async function fetchMomentumRadar(
  timeWindow: TimeWindow = '7d', 
  page: number = 1, 
  limit: number = 30
): Promise<Repository[]> {
  const res = await fetch(`${API_BASE}/momentum/radar?time_window=${timeWindow}&page=${page}&limit=${limit}`);
  if (!res.ok) throw new Error('Failed to fetch momentum radar');
  return res.json();
}

export async function fetchTopics(
  mode: SortMode = 'momentum', 
  timeWindow: TimeWindow = '7d', 
  limitPerTopic: number = 30
): Promise<TopicCategory[]> {
  const res = await fetch(`${API_BASE}/topics?mode=${mode}&time_window=${timeWindow}&limit_per_topic=${limitPerTopic}`);
  if (!res.ok) throw new Error('Failed to fetch topic categories');
  return res.json();
}

export async function fetchAllTopics(q?: string, limit: number = 2000): Promise<TopicItem[]> {
  const query = new URLSearchParams();
  if (q) query.set('q', q);
  query.set('limit', limit.toString());
  const res = await fetch(`${API_BASE}/topics/all?${query.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch all topics');
  return res.json();
}

export async function fetchWatchlist(): Promise<Repository[]> {
  const res = await fetch(`${API_BASE}/watchlist`);
  if (!res.ok) throw new Error('Failed to fetch watchlist');
  return res.json();
}

export async function toggleWatchlist(repoId: number, notes?: string): Promise<{ is_saved: boolean }> {
  const res = await fetch(`${API_BASE}/watchlist`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ repo_id: repoId, notes })
  });
  if (!res.ok) throw new Error('Failed to toggle watchlist');
  return res.json();
}

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const res = await fetch(`${API_BASE}/status`);
  if (!res.ok) throw new Error('Failed to fetch system status');
  return res.json();
}

export async function triggerRefresh(): Promise<any> {
  const res = await fetch(`${API_BASE}/status/refresh`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to trigger refresh');
  return res.json();
}
