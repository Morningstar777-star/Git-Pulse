import { 
  Repository, 
  RepositoryDetail, 
  TopicCategory, 
  TopicItem, 
  SystemStatus, 
  SortMode, 
  TimeWindow, 
  PopularitySortBy,
  User,
  AuthResponse
} from '../types';

const API_BASE = '/api';
const TOKEN_KEY = 'gitpulse_auth_token';

export function getAuthToken(): string | null {
  if (typeof window !== 'undefined') {
    return localStorage.getItem(TOKEN_KEY);
  }
  return null;
}

export function setAuthToken(token: string | null): void {
  if (typeof window !== 'undefined') {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
  }
}

function getAuthHeaders(): HeadersInit {
  const token = getAuthToken();
  const headers: Record<string, string> = {
    'Content-Type': 'application/json'
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

// ==========================================
// User Authentication Endpoints
// ==========================================

export async function signUp(email: string, password: string, name?: string): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password, name })
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Sign up failed');
  setAuthToken(data.token);
  return data;
}

export async function signIn(email: string, password: string): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/auth/signin`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Sign in failed');
  setAuthToken(data.token);
  return data;
}

export async function fetchMe(): Promise<User | null> {
  const token = getAuthToken();
  if (!token) return null;

  try {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: getAuthHeaders()
    });
    if (!res.ok) {
      if (res.status === 401) setAuthToken(null);
      return null;
    }
    const data = await res.json();
    return data.user;
  } catch {
    return null;
  }
}

export async function forgotPassword(email: string): Promise<{ status: string; message: string; reset_code?: string; reset_token?: string }> {
  const res = await fetch(`${API_BASE}/auth/forgot-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email })
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Password reset request failed');
  return data;
}

export async function resetPassword(email: string, reset_code: string, new_password: string): Promise<AuthResponse> {
  const res = await fetch(`${API_BASE}/auth/reset-password`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, reset_code, new_password })
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || 'Password reset failed');
  setAuthToken(data.token);
  return data;
}

export async function signOut(): Promise<void> {
  try {
    await fetch(`${API_BASE}/auth/signout`, {
      method: 'POST',
      headers: getAuthHeaders()
    });
  } catch {
    // Ignore signout network errors
  } finally {
    setAuthToken(null);
  }
}

// ==========================================
// Core Repository & Intelligence Endpoints
// ==========================================

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

  const res = await fetch(`${API_BASE}/repositories?${query.toString()}`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error(`Failed to fetch repositories (${res.status})`);
  return res.json();
}

export async function fetchRepositoryDetail(id: number): Promise<RepositoryDetail> {
  const res = await fetch(`${API_BASE}/repositories/${id}`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error(`Failed to fetch repository #${id}`);
  return res.json();
}

export async function fetchMomentumRadar(
  timeWindow: TimeWindow = '7d', 
  page: number = 1, 
  limit: number = 30
): Promise<Repository[]> {
  const res = await fetch(`${API_BASE}/momentum/radar?time_window=${timeWindow}&page=${page}&limit=${limit}`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error('Failed to fetch momentum radar');
  return res.json();
}

export async function fetchTopics(
  mode: SortMode = 'momentum', 
  timeWindow: TimeWindow = '7d', 
  limitPerTopic: number = 20
): Promise<TopicCategory[]> {
  const res = await fetch(`${API_BASE}/topics?mode=${mode}&time_window=${timeWindow}&limit_per_topic=${limitPerTopic}`, {
    headers: getAuthHeaders()
  });
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
  const token = getAuthToken();
  if (!token) return [];

  const res = await fetch(`${API_BASE}/watchlist`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) {
    if (res.status === 401) return [];
    throw new Error('Failed to fetch watchlist');
  }
  return res.json();
}

export async function toggleWatchlist(repoId: number, notes?: string): Promise<{ is_saved: boolean }> {
  const token = getAuthToken();
  if (!token) {
    throw new Error('SIGN_IN_REQUIRED');
  }

  const res = await fetch(`${API_BASE}/watchlist`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: JSON.stringify({ repo_id: repoId, notes })
  });
  const data = await res.json();
  if (!res.ok) {
    if (res.status === 401) throw new Error('SIGN_IN_REQUIRED');
    throw new Error(data.detail || 'Failed to toggle watchlist');
  }
  return data;
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
