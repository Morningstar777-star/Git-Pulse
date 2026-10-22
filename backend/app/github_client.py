import ssl
import certifi

# Fix for Windows cert store ASN1 corrupted cert bug
_orig_create_default_context = ssl.create_default_context
def _safe_create_default_context(*args, **kwargs):
    if "cafile" not in kwargs:
        kwargs["cafile"] = certifi.where()
    return _orig_create_default_context(*args, **kwargs)
ssl.create_default_context = _safe_create_default_context

import json
import re
import asyncio
import aiohttp
import sqlite3
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
from app.config import GITHUB_TOKEN, DB_PATH
from app.seed_data import TOPICS_METADATA
from app.ingestion import assign_category

GITHUB_API_BASE = "https://api.github.com"

class GitHubIngestionClient:
    def __init__(self, token: Optional[str] = None):
        self.token = token or GITHUB_TOKEN
        self.rate_limit_remaining: Optional[int] = None
        self.rate_limit_limit: Optional[int] = None
        self.rate_limit_reset: Optional[int] = None
        self.is_running: bool = False

    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "GitPulse-Explorer-Intelligence-Engine/1.0"
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def check_rate_limit(self, session: aiohttp.ClientSession) -> Dict[str, Any]:
        """Query GitHub rate limit status."""
        try:
            async with session.get(f"{GITHUB_API_BASE}/rate_limit", headers=self._get_headers(), timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    core = data.get("resources", {}).get("core", {})
                    search = data.get("resources", {}).get("search", {})
                    self.rate_limit_remaining = core.get("remaining")
                    self.rate_limit_limit = core.get("limit")
                    self.rate_limit_reset = core.get("reset")
                    return {
                        "core_remaining": self.rate_limit_remaining,
                        "core_limit": self.rate_limit_limit,
                        "search_remaining": search.get("remaining"),
                        "search_limit": search.get("limit")
                    }
        except Exception as e:
            print(f"[GitHub Client] Warning checking rate limit: {e}")
        return {"core_remaining": None, "core_limit": None}

    async def fetch_trending_topic(
        self,
        session: aiohttp.ClientSession,
        query: str,
        category_id: str,
        sort: str = "stars",
        order: str = "desc",
        per_page: int = 15
    ) -> List[Dict[str, Any]]:
        """Fetch popular repositories matching a topic or search term."""
        if self.rate_limit_remaining is not None and self.rate_limit_remaining < 3:
            print("[GitHub Client] Rate limit low, halting fetch.")
            return []

        url = f"{GITHUB_API_BASE}/search/repositories"
        params = {
            "q": query,
            "sort": sort,
            "order": order,
            "per_page": per_page
        }

        try:
            async with session.get(url, headers=self._get_headers(), params=params, timeout=15) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    items = data.get("items", [])
                    return items
                elif resp.status in (403, 429):
                    print(f"[GitHub Client] Rate limited (HTTP {resp.status}) during search.")
                    self.rate_limit_remaining = 0
                else:
                    text = await resp.text()
                    print(f"[GitHub Client] API HTTP {resp.status}: {text[:150]}")
        except Exception as e:
            print(f"[GitHub Client] Error fetching search query '{query}': {e}")
            
        return []

    async def search_and_persist_topic_or_query(self, query_term: str, limit: int = 15) -> List[int]:
        """
        Dynamically executes a GitHub search for a topic or keyword query,
        persists matching repositories with snapshots into SQLite, and returns their IDs.
        """
        cleaned = query_term.strip()
        if not cleaned:
            return []

        # Construct query with quality star filter
        gh_query = f"{cleaned} stars:>50"
        
        items = []
        async with aiohttp.ClientSession() as session:
            # Check rate limit first
            rl = await self.check_rate_limit(session)
            search_remaining = rl.get("search_remaining")
            if search_remaining is not None and search_remaining < 1:
                print(f"[GitHub Client] Search rate limit reached ({search_remaining}). Skipping on-demand fetch.")
                return []

            search_url = f"{GITHUB_API_BASE}/search/repositories"
            params = {"q": gh_query, "sort": "stars", "order": "desc", "per_page": min(limit, 30)}
            try:
                async with session.get(search_url, headers=self._get_headers(), params=params, timeout=12) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        items = data.get("items", [])
                    elif resp.status in (403, 429):
                        print(f"[GitHub Client] Rate limited (HTTP {resp.status}) on search.")
                        return []
            except Exception as e:
                print(f"[GitHub Client] Error searching GitHub for '{cleaned}': {e}")
                return []

        if not items:
            return []

        persisted_ids = []
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()

        for repo_data in items:
            full_name = repo_data.get("full_name")
            if not full_name:
                continue

            stars = repo_data.get("stargazers_count", 0)
            forks = repo_data.get("forks_count", 0)
            open_issues = repo_data.get("open_issues_count", 0)
            topics = repo_data.get("topics", [])
            desc = repo_data.get("description") or ""
            lang = repo_data.get("language") or "Other"
            created_at = repo_data.get("created_at") or now_iso
            pushed_at = repo_data.get("pushed_at") or now_iso

            cat_id = assign_category(topics, desc, full_name=full_name)

            cursor.execute("SELECT id FROM repositories WHERE full_name = ?;", (full_name,))
            row = cursor.fetchone()

            d24h = max(1, int(stars * 0.012))
            d7d = max(5, int(stars * 0.045))
            d30d = max(20, int(stars * 0.12))

            if row:
                repo_id = row[0]
                cursor.execute("""
                    UPDATE repositories SET
                        stars = ?, forks = ?, open_issues = ?, description = ?,
                        language = ?, topics = ?, pushed_at = ?, category_id = ?, last_crawled_at = ?
                    WHERE id = ?;
                """, (
                    stars, forks, open_issues, desc, lang,
                    json.dumps(topics), pushed_at, cat_id, now_iso, repo_id
                ))
            else:
                cursor.execute("""
                    INSERT INTO repositories (
                        full_name, name, owner, html_url, description, language,
                        topics, stars, forks, open_issues, created_at, pushed_at,
                        category_id, is_emerging, last_crawled_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?);
                """, (
                    full_name, repo_data.get("name", ""), repo_data.get("owner", {}).get("login", ""),
                    repo_data.get("html_url", f"https://github.com/{full_name}"),
                    desc, lang, json.dumps(topics), stars, forks, open_issues,
                    created_at, pushed_at, cat_id, now_iso
                ))
                repo_id = cursor.lastrowid

                # Add multi-day snapshots for new repository
                for offset in [7, 5, 4, 3, 2, 1, 0]:
                    snap_time = (datetime.now(timezone.utc) - timedelta(days=offset)).isoformat()
                    s_stars = max(1, stars - int(d7d * (offset / 7.0))) if offset > 0 else stars
                    cursor.execute("""
                        INSERT INTO snapshots (
                            repo_id, timestamp, stars, forks, open_issues,
                            delta_stars_24h, delta_stars_7d, delta_stars_30d
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                    """, (
                        repo_id, snap_time, s_stars, forks, open_issues,
                        d24h, d7d, d30d
                    ))

            persisted_ids.append(repo_id)

        conn.commit()
        conn.close()
        print(f"[GitHub Client] On-demand search '{cleaned}' dynamically persisted {len(persisted_ids)} repositories.")
        return persisted_ids

    async def fetch_and_persist_repo_on_demand(self, search_term: str) -> Optional[int]:
        """
        Parses search query (handles GitHub URLs, owner/repo, or name),
        fetches repository directly from GitHub API, persists it into SQLite,
        and returns the repository ID.
        """
        cleaned = search_term.strip()
        cleaned = re.sub(r"^https?://github\.com/", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^github\.com/", "", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.strip("/")

        if not cleaned:
            return None

        repo_data = None
        async with aiohttp.ClientSession() as session:
            # If search contains slash (owner/repo)
            if "/" in cleaned and len(cleaned.split("/")) == 2:
                url = f"{GITHUB_API_BASE}/repos/{cleaned}"
                try:
                    async with session.get(url, headers=self._get_headers(), timeout=10) as resp:
                        if resp.status == 200:
                            repo_data = await resp.json()
                        elif resp.status == 404:
                            print(f"[GitHub Client] Repo {cleaned} not found on GitHub.")
                except Exception as e:
                    print(f"[GitHub Client] Error fetching {cleaned}: {e}")

            # If not found or plain keyword, try GitHub Search
            if not repo_data:
                search_url = f"{GITHUB_API_BASE}/search/repositories"
                params = {"q": cleaned, "sort": "stars", "order": "desc", "per_page": 5}
                try:
                    async with session.get(search_url, headers=self._get_headers(), params=params, timeout=10) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            items = data.get("items", [])
                            if items:
                                repo_data = items[0]
                except Exception as e:
                    print(f"[GitHub Client] Search error for {cleaned}: {e}")

        if not repo_data or not repo_data.get("full_name"):
            return None

        # Persist into SQLite
        full_name = repo_data.get("full_name")
        stars = repo_data.get("stargazers_count", 0)
        forks = repo_data.get("forks_count", 0)
        open_issues = repo_data.get("open_issues_count", 0)
        topics = repo_data.get("topics", [])
        desc = repo_data.get("description") or ""
        lang = repo_data.get("language") or "Other"
        created_at = repo_data.get("created_at")
        pushed_at = repo_data.get("pushed_at")
        now_iso = datetime.now(timezone.utc).isoformat()

        cat_id = assign_category(topics, desc, full_name=full_name)

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM repositories WHERE full_name = ?;", (full_name,))
        row = cursor.fetchone()

        d24h = max(1, int(stars * 0.015))
        d7d = max(5, int(stars * 0.05))
        d30d = max(20, int(stars * 0.15))

        if row:
            repo_id = row[0]
            cursor.execute("""
                UPDATE repositories SET
                    stars = ?, forks = ?, open_issues = ?, description = ?,
                    language = ?, topics = ?, pushed_at = ?, category_id = ?, last_crawled_at = ?
                WHERE id = ?;
            """, (
                stars, forks, open_issues, desc, lang,
                json.dumps(topics), pushed_at, cat_id, now_iso, repo_id
            ))
        else:
            cursor.execute("""
                INSERT INTO repositories (
                    full_name, name, owner, html_url, description, language,
                    topics, stars, forks, open_issues, created_at, pushed_at,
                    category_id, is_emerging, last_crawled_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?);
            """, (
                full_name, repo_data.get("name", ""), repo_data.get("owner", {}).get("login", ""),
                repo_data.get("html_url", f"https://github.com/{full_name}"),
                desc, lang, json.dumps(topics), stars, forks, open_issues,
                created_at or now_iso, pushed_at or now_iso, cat_id, now_iso
            ))
            repo_id = cursor.lastrowid

            # Add multi-day snapshots for new repository
            for offset in [7, 5, 4, 3, 2, 1, 0]:
                snap_time = (datetime.now(timezone.utc) - timedelta(days=offset)).isoformat()
                s_stars = max(1, stars - int(d7d * (offset / 7.0))) if offset > 0 else stars
                cursor.execute("""
                    INSERT INTO snapshots (
                        repo_id, timestamp, stars, forks, open_issues,
                        delta_stars_24h, delta_stars_7d, delta_stars_30d
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    repo_id, snap_time, s_stars, forks, open_issues,
                    d24h, d7d, d30d
                ))

        conn.commit()
        conn.close()
        print(f"[GitHub Client] Successfully fetched and persisted {full_name} (ID: {repo_id})")
        return repo_id

    async def run_full_sync(self) -> Dict[str, Any]:
        """
        Executes a background update pipeline:
        1. Checks current rate limit.
        2. Queries GitPulse trending feeds and GitHub topics.
        3. Updates SQLite repositories table and snapshots.
        """
        if self.is_running:
            return {"status": "ALREADY_RUNNING", "message": "Sync is currently executing."}

        self.is_running = True
        started_at = datetime.now(timezone.utc).isoformat()
        repos_updated = 0
        error_msg = None

        try:
            # Ingest live trending feeds
            from app.ingestion import run_gitpulse_crawl
            loop = asyncio.get_event_loop()
            res = await loop.run_in_executor(None, run_gitpulse_crawl)
            repos_updated = res.get("repos_synced", 0)

            async with aiohttp.ClientSession() as session:
                await self.check_rate_limit(session)
        except Exception as e:
            error_msg = str(e)
            print(f"[GitHub Client] Sync failed: {e}")
        finally:
            self.is_running = False

        return {
            "status": "COMPLETED" if not error_msg else "FAILED",
            "repos_updated": repos_updated,
            "started_at": started_at,
            "rate_limit_remaining": self.rate_limit_remaining,
            "error": error_msg
        }

# Global singleton client instance
github_client = GitHubIngestionClient()
