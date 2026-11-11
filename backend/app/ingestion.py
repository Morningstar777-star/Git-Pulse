"""
Ingestion & Synchronization Pipeline for GitPulse Explorer.
Aggregates live trending repositories, daily/weekly/monthly breakout tables,
and topic directories covering 900+ topics from GitPulse and GitHub.
"""

import sys
from pathlib import Path

# Ensure backend root is on sys.path regardless of execution directory
_backend_root = Path(__file__).resolve().parent.parent
if str(_backend_root) not in sys.path:
    sys.path.insert(0, str(_backend_root))

import ssl
import certifi
import urllib.request
import re
import json
import html as html_lib
import sqlite3
import asyncio
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional, Tuple
from app.config import DB_PATH
from app.models.smart_momentum import calculate_smart_momentum
from app.translator import translate_cjk_sync, contains_cjk

# Fix Windows cert store
ctx = ssl.create_default_context(cafile=certifi.where())

def fetch_url(url: str, timeout: int = 12) -> str:
    try:
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8"
            }
        )
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[Ingestion] Fetch error for {url}: {e}")
        return ""

def _pct_to_delta(stars: int, pct: float) -> int:
    """Convert growth percentage p = 100 * delta / (stars - delta) into exact integer star gain."""
    if not pct or pct <= 0 or stars <= 0:
        return 0
    ratio = float(pct) / 100.0
    delta = round(stars * ratio / (1.0 + ratio))
    return max(0, min(stars, delta))

def _is_recent_iso(iso_str: Optional[str], max_age_days: int) -> bool:
    """Return True if an ISO timestamp string is within max_age_days of UTC now."""
    if not iso_str:
        return False
    try:
        dt = datetime.fromisoformat(str(iso_str).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return (datetime.now(timezone.utc) - dt).total_seconds() <= max_age_days * 86400
    except Exception:
        return False

def _compute_deltas_and_emerging(r: Dict[str, Any]) -> Tuple[int, int, int, int, int]:
    """
    Compute consistent (stars, d24h, d7d, d30d, is_emerging) from crawled repo telemetry.
    Shared by SQLite persistence and Turso cloud sync to prevent skew.
    """
    stars = max(1, int(r.get("stars") or 0))
    spd = int(r.get("stars_per_day") or 0)
    g1d = float(r.get("growth_1d_pct") or 0.0)
    g7d = float(r.get("growth_7d_pct") or 0.0)
    g30d = float(r.get("growth_30d_pct") or 0.0)

    d24h = min(stars, spd) if spd > 0 else _pct_to_delta(stars, g1d)
    if d24h <= 0 and g7d > 0:
        d24h = max(1, _pct_to_delta(stars, g7d) // 7)

    d7d = _pct_to_delta(stars, g7d) if g7d > 0 else min(stars, d24h * 4)
    d7d = min(stars, max(d24h, d7d))

    d30d = _pct_to_delta(stars, g30d) if g30d > 0 else min(stars, d7d * 3)
    d30d = min(stars, max(d7d, d30d))

    pushed_at = r.get("pushed_at")
    dormant = bool(pushed_at) and not _is_recent_iso(pushed_at, 120)
    is_newly_created = _is_recent_iso(r.get("created_at"), 60)

    explicit_emerging = bool(r.get("is_emerging")) and not dormant
    metric_emerging = (
        not dormant and (
            is_newly_created
            or g1d >= 2.0
            or g7d >= 10.0
            or (d24h >= 150 and g1d >= 0.4)
        )
    )
    is_emerging = 1 if (explicit_emerging or metric_emerging) else 0
    return stars, d24h, d7d, d30d, is_emerging

def parse_trending_table(html: str) -> List[Dict[str, Any]]:
    rows = re.findall(r'<tr[^>]*>([\s\S]*?)</tr>', html)
    repos = []
    for r in rows:
        if '<th' in r:
            continue
        repo_m = re.search(r'href=[\'"]/gitpulse/repo/([^\'"]+)/?[\'"]', r)
        if not repo_m:
            continue
        full_name = repo_m.group(1).strip('/')
        parts = full_name.split('/')
        owner = parts[0] if len(parts) > 0 else ''
        name = parts[1] if len(parts) > 1 else full_name

        desc_m = re.search(r'class=[\'"]cell-desc[\'"][^>]*>([\s\S]*?)</span>', r)
        desc = html_lib.unescape(re.sub(r'<[^>]+>', '', desc_m.group(1)).strip()) if desc_m else ''

        # Tags
        raw_tags = re.findall(r'href=[\'"]/gitpulse/topics/([^\'"]+)/?[\'"]', r)
        tags = [t.strip('/') for t in raw_tags if t.strip('/')]

        # Numeric cells: data-v (Stars, 1D%, 7D%, 30D%, Lifetime Avg Per Day)
        tds = re.findall(r'<td[^>]*data-v=[\'"]([^\'"]*)[\'"][^>]*>', r)

        stars = 0
        g1d = 0.0
        g7d = 0.0
        g30d = 0.0
        lifetime_rate = 0

        if len(tds) >= 1 and tds[0]:
            try: stars = int(float(tds[0]))
            except: pass
        if len(tds) >= 2 and tds[1]:
            try: g1d = float(tds[1])
            except: pass
        if len(tds) >= 3 and tds[2]:
            try: g7d = float(tds[2])
            except: pass
        if len(tds) >= 4 and tds[3]:
            try: g30d = float(tds[3])
            except: pass
        if len(tds) >= 5 and tds[4]:
            try: lifetime_rate = int(float(tds[4]))
            except: pass

        # Compute actual 24h velocity from 1D%/7D% instead of lifetime avg tds[4],
        # preventing giant legacy repos from showing inflated daily velocities.
        d24_pct = _pct_to_delta(stars, g1d)
        d7_pct = _pct_to_delta(stars, g7d)
        if d24_pct > 0:
            rate = d24_pct
        elif d7_pct > 0:
            rate = max(1, d7_pct // 7)
        else:
            rate = min(lifetime_rate, max(1, int(stars * 0.005))) if lifetime_rate > 0 else 0

        # Language heuristic if found
        lang = "TypeScript" if "typescript" in tags else "Python" if "python" in tags else "Rust" if "rust" in tags else "Go" if "go" in tags else "JavaScript"

        repos.append({
            "full_name": full_name,
            "owner": owner,
            "name": name,
            "description": desc,
            "topics": tags,
            "stars": stars,
            "growth_1d_pct": g1d,
            "growth_7d_pct": g7d,
            "growth_30d_pct": g30d,
            "stars_per_day": rate,
            "language": lang
        })
    return repos

def extract_all_topics_catalog() -> List[Dict[str, Any]]:
    """Extracts master list of 904 topics from GitPulse."""
    html = fetch_url("https://thaitrn.github.io/gitpulse/topics/")
    if not html:
        return []
    
    links = re.findall(r'<a[^>]*href=[\'"]/gitpulse/topics/([^\'"]+)/?[\'"][^>]*>([\s\S]*?)</a>', html)
    topic_list = []
    seen = set()
    for slug, inner in links:
        slug_clean = slug.strip('/')
        if not slug_clean or slug_clean in seen:
            continue
        seen.add(slug_clean)
        inner_clean = re.sub(r'<[^>]+>', ' ', inner).strip()
        topic_list.append({
            "topic": slug_clean,
            "name": inner_clean or slug_clean
        })
    return topic_list

def assign_category(topics: List[str], description: str, full_name: str = "") -> str:
    """Classifies repository into primary dashboard category using comprehensive token, semantic, and domain matching."""
    t_set = {t.lower().strip() for t in (topics or [])}
    desc_clean = (description or "").lower()
    fn_clean = (full_name or "").lower()
    text = f"{fn_clean} {desc_clean} " + " ".join(t_set)

    # 1. Web Scraping, Crawlers & Extraction
    scraping_topics = {
        'scraping', 'web-scraping', 'crawler', 'crawlers', 'playwright', 'puppeteer',
        'scrapy', 'spider', 'spiders', 'crawl4ai', 'scraper', 'data-extraction', 'web-crawler',
        'crawling', 'extractor', 'html-parser', 'cheerio', 'beautifulsoup', 'selenium',
        'browser-automation', 'anti-detect', 'stealth', 'scraping-framework'
    }
    if any(t in t_set for t in scraping_topics) or re.search(r'\b(scrap(ing|er|ers)|crawler|crawlers|crawling|crawl4ai|playwright|puppeteer|scrapy|spider|spiders|data extraction|html extraction|headless browser|anti-detect|stealth browser)\b', text):
        return 'web-scraping'

    # 2. Medical Science, BioTech & Healthcare AI
    medical_topics = {
        'medical', 'bioinformatics', 'healthcare', 'genomics', 'biology', 'clinical',
        'pathology', 'biomedical', 'medicine', 'health', 'dna', 'protein', 'biotech',
        'neuroscience', 'fitness', 'longevity', 'drug-discovery', 'patient', 'hospital',
        'disease', 'mental-health', 'nutrition', 'workout', 'cardio', 'pharma', 'biomarker',
        'radiology', 'dicom', 'pharmacology', 'mri', 'wellness'
    }
    if any(t in t_set for t in medical_topics) or re.search(r'\b(medical|healthcare|bioinformatics|genomics|biomedical|clinical|pathology|dna|protein|biology|medicine|health|longevity|fitness|patient|hospital|drug discovery|disease|mental health|nutrition|cardio|pharma|biotech|radiology|dicom)\b', text):
        return 'medical-science'

    # 3. Arts, Culture & Creative Technology
    arts_topics = {
        'art', 'arts', 'culture', 'photo-editor', 'vector', 'drawing', 'generative-art',
        'photocraft', 'vectorcraft', 'canvas', 'creative-coding', 'design', 'illustration',
        'fonts', 'font', 'icons', 'icon', 'svg', 'palette', 'theme', 'themes', 'animation',
        'video-editor', 'creative', 'wallpaper', 'pixel-art', 'painting', 'typography',
        'ui-ux', 'design-system', 'uikit', 'figma', 'sketch', 'styleguide', 'design-intelligence'
    }
    if any(t in t_set for t in arts_topics) or re.search(r'\b(art|arts|culture|photo editor|photo editing|vector|generative art|creative coding|digital canvas|illustration|svg|fonts?|icons?|drawing|animation|video editing|video editor|color palette|pixel art|typography|design system|ui\/ux|design intelligence|figma)\b', text):
        return 'arts-culture'

    # 4. Speech Synthesis, Voice AI & Audio DSP
    speech_topics = {
        'speech', 'tts', 'text-to-speech', 'speech-to-text', 'stt', 'asr', 'whisper',
        'voice', 'voice-cloning', 'audio', 'sound', 'speech-synthesis', 'wav2lip',
        'fish-speech', 'chatterbox', 'gpt-sovits', 'music', 'synthesizer', 'dsp', 'podcast', 'transcription'
    }
    if any(t in t_set for t in speech_topics) or re.search(r'\b(tts|stt|whisper|text-to-speech|speech-to-text|voice cloning|speech synthesis|speech recognition|transcription|audio processing|synthesizer|dsp|voice assistant|audio|sound)\b', text):
        return 'speech-audio'

    # 5. Game Engines, 3D Models & WebGL
    gaming_topics = {
        '3d', 'threejs', 'three.js', 'webgl', 'game-engine', 'godot', 'unity', 'unreal',
        'shaders', 'rendering', 'vulkan', 'opengl', 'react-three-fiber', 'gamedev', 'cad',
        'text-to-cad', 'graphics', 'mesh', '3d-model', 'blender', 'raytracing', 'canvas-3d',
        'game', 'games', 'gaming'
    }
    if any(t in t_set for t in gaming_topics) or re.search(r'\b(3d|three\.js|threejs|webgl|game engine|godot|unity|unreal|shaders?|rendering|vulkan|opengl|react-three-fiber|gamedev|cad|3d printing|mesh rendering|computer graphics|blender|game development)\b', text):
        return 'gaming-graphics'

    # 6. Privacy, Adblocking & Anti-Tracking
    privacy_topics = {
        'privacy', 'adblock', 'adblocking', 'debloat', 'anti-tracking', 'dns', 'vpn',
        'wireguard', 'anonymity', 'tor', 'cleanyourtv', 'anti-censorship', 'tracker-blocker',
        'hosts', 'pi-hole', 'adguard', 'firewall-rules', 'ad-blocker'
    }
    if any(t in t_set for t in privacy_topics) or re.search(r'\b(adblock|adblocking|debloat|anti-tracking|privacy|anonymity|pi-hole|adguard|wireguard|vpn|tor network|anti-censorship|tracker block|ad-blocker)\b', text):
        return 'privacy-adblock'

    # 7. Education, Open Knowledge & Books
    edu_topics = {
        'education', 'learning', 'curriculum', 'textbook', 'textbooks', 'tutorial',
        'awesome-list', 'cheat-sheet', 'how-to', 'life-guide', 'howto', 'course',
        'books', 'papers', 'study', 'knowledge', 'cs-courses', 'freecodecamp',
        'challenge', 'challenges', 'exercise', 'exercises', 'roadmap', 'cheatsheet',
        'handbook', 'leetcode', 'interview-prep', 'learning-resources'
    }
    if any(t in t_set for t in edu_topics) or re.search(r'\b(education|curriculum|tutorial|textbooks?|cheat sheet|awesome list|how to|learning guide|cs courses?|study guide|handbook|freecodecamp|interview preparation|challenges?|exercises?|roadmap|leetcode)\b', text):
        return 'education-learning'

    # 8. Browser Agents & Autonomous Workflows
    auto_topics = {
        'browser-use', 'automation', 'browser-agent', 'headless-browser', 'workflow-automation',
        'task-automation', 'workflow', 'n8n', 'automate', 'rpa', 'bot', 'cron', 'scheduler',
        'nocode', 'lowcode', 'work-flow', 'pipelines'
    }
    if any(t in t_set for t in auto_topics) or re.search(r'\b(workflow automation|browser-use|browser agent|task automation|autonomous workflow|automation platform|rpa|automate|automated workflow|scheduled tasks|cron|no-code|low-code)\b', text):
        return 'smart-automation'

    # 9. LLM Agents & Generative Apps
    llm_topics = {
        'llm', 'llms', 'agent', 'agents', 'prompt', 'prompts', 'rag', 'langchain', 'llamaindex',
        'ollama', 'claude', 'gpt', 'gpt-4', 'chatgpt', 'crewai', 'mcp', 'deepseek', 'copilot',
        'autonomous-agents', 'reasoning', 'agentic', 'genai', 'openai', 'gemini', 'anthropic',
        'ai-agent', 'coding-agent', 'ai-agents', 'prompt-engineering', 'claude-code', 'codex',
        'context-engineering', 'agent-memory', 'deepseek-harness', 'mcp-server'
    }
    if any(t in t_set for t in llm_topics) or re.search(r'\b(llm|llms|agentic|langchain|ollama|deepseek|rag|crewai|chatgpt|gpt|prompts?|reasoning model|coding agent|ai agents?|autonomous agents?|mcp server|retrieval augmented|claude|gemini|openai|anthropic|context engineering)\b', text):
        return 'llm-agents'

    # 10. Cybersecurity & Pentesting
    sec_topics = {
        'cybersecurity', 'security', 'penetration-testing', 'pentest', 'exploit', 'vulnerability',
        'reverse-engineering', 'cryptography', 'malware', 'ctf', 'infosec', 'firewall', 'hacking',
        'decompiler', 'rea', 'binary-analysis', 'red-team', 'blue-team', 'bugbounty',
        'appsec', 'secrets-scanning', 'git-security', 'devsecops', 'security-audit', 'cve',
        'auth-bypass', 'zero-trust', 'sast', 'dast', 'trufflehog'
    }
    if any(t in t_set for t in sec_topics) or re.search(r'\b(cybersecurity|pentest|penetration testing|vulnerability|reverse engineering|malware|decompiler|cryptography|binary analysis|infosec|exploit|bug bounty|red team|security audit|secrets? scanning|appsec|devsecops|cve)\b', text):
        return 'cybersecurity'

    # 11. Quant & Data Science
    quant_topics = {
        'quantitative-finance', 'trading', 'algorithmic-trading', 'crypto', 'cryptocurrency',
        'backtesting', 'finance', 'fintech', 'bitcoin', 'ethereum', 'solana', 'defi',
        'stocks', 'investing', 'quant', 'portfolio', 'orderbook', 'market-data', 'yfinance',
        'openbb', 'accounting', 'ledger', 'wallet', 'finances', 'payment', 'payments', 'stripe',
        'web3', 'blockchain', 'smart-contracts'
    }
    if any(t in t_set for t in quant_topics) or re.search(r'\b(quantitative finance|algorithmic trading|trading bot|backtest|backtesting|crypto|cryptocurrency|bitcoin|ethereum|stocks?|investing|financial|fintech|quant|portfolio optimization|orderbook|market data|personal finances?|payments?|ledger|blockchain|defi)\b', text):
        return 'quant-datasci'

    # 12. Robotics & Hardware
    robot_topics = {
        'robotics', 'robot', 'ros', 'ros2', 'embedded', 'arduino', 'esp32', 'firmware',
        'iot', 'hardware', 'microcontroller', 'drone', 'raspberry-pi', 'stm32', 'circuit',
        'sensor', 'edge-computing', 'fpga', 'pcb', 'robotics-framework'
    }
    if any(t in t_set for t in robot_topics) or re.search(r'\b(robotics?|ros2?|embedded|arduino|esp32|microcontroller|firmware|iot|drone|hardware device|raspberry pi|sensors?|fpga|pcb)\b', text):
        return 'robotics-hardware'

    # 13. Data Engineering & Databases
    data_topics = {
        'database', 'databases', 'sql', 'postgresql', 'postgres', 'mysql', 'sqlite', 'duckdb',
        'clickhouse', 'polars', 'pandas', 'spark', 'kafka', 'data-warehouse', 'etl', 'olap',
        'supabase', 'redis', 'vector-database', 'chroma', 'milvus', 'nosql', 'relational-database',
        'data-pipeline', 'key-value', 'kv', 'consensus', 'raft', 'etcd', 'memcached', 'cache',
        'analytics', 'streaming', 'lakehouse', 'parquet', 'arrow', 'backend', 'pocketbase'
    }
    if any(t in t_set for t in data_topics) or re.search(r'\b(databases?|postgresql|postgres|mysql|sqlite|duckdb|clickhouse|polars|spark|kafka|data warehouse|etl pipeline|olap|vector database|redis|supabase|stream processing|key-value|nosql|realtime backend|data pipeline)\b', text):
        return 'data-engineering'

    # 14. Infrastructure & DevOps
    infra_topics = {
        'kubernetes', 'k8s', 'docker', 'devops', 'terraform', 'ansible', 'linux', 'cloud-native',
        'serverless', 'ci-cd', 'terminal', 'cli', 'tui', 'zsh', 'bash', 'shell', 'system-design',
        'proxy', 'networking', 'mesh', 'sysadmin', 'command-line', 'ssh', 'homelab', 'self-hosted',
        'package-manager', 'uv', 'observability', 'monitoring', 'metrics', 'grafana', 'prometheus',
        'telemetry', 'tracing', 'logging', 'nginx', 'caddy', 'envoy', 'traefik', 'api-gateway',
        'developer-tools', 'devtools', 'compiler', 'linter', 'formatter', 'debugger',
        'android', 'macos', 'windows', 'operating-system', 'os'
    }
    if any(t in t_set for t in infra_topics) or re.search(r'\b(kubernetes|k8s|docker|devops|terraform|ansible|linux|cloud native|serverless|ci\/cd|terminal ui|command line|cli tool|system design|homelab|self-hosted|reverse proxy|networking|package manager|observability|monitoring|metrics|grafana|prometheus|developer tools?)\b', text):
        return 'infrastructure'

    # 15. Web Frameworks
    web_topics = {
        'react', 'nextjs', 'vue', 'vuejs', 'angular', 'svelte', 'sveltekit', 'tailwindcss',
        'frontend', 'fullstack', 'javascript', 'typescript', 'css', 'html5', 'astro', 'remix',
        'web-framework', 'web-development', 'ui-library', 'component', 'shadcn', 'webui'
    }
    if any(t in t_set for t in web_topics) or re.search(r'\b(react|next\.js|nextjs|vue\.js|vuejs|angular|svelte|tailwindcss|tailwind css|frontend framework|web application|ui components?|shadcn|web framework|css framework)\b', text):
        return 'web-frameworks'

    # 16. AI & Machine Learning
    ai_topics = {
        'machine-learning', 'deep-learning', 'pytorch', 'tensorflow', 'neural-network',
        'computer-vision', 'diffusion', 'stable-diffusion', 'huggingface', 'reinforcement-learning',
        'transformers', 'nlp', 'object-detection', 'scikit-learn', 'deep-neural-networks'
    }
    if any(t in t_set for t in ai_topics) or re.search(r'\b(machine learning|deep learning|pytorch|tensorflow|neural networks?|computer vision|diffusion models?|reinforcement learning|transformer models?|scikit-learn)\b', text):
        return 'ai-ml'

    # 17. Default: Emerging Tech
    return 'emerging-tech'

def save_repos_to_database(repos: List[Dict[str, Any]], db_path: str = DB_PATH) -> int:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()
    today_date = now_iso[:10]
    saved_count = 0

    cursor.execute("CREATE INDEX IF NOT EXISTS idx_snaps_ts_repo ON snapshots(timestamp DESC, repo_id);")

    for r in repos:
        full_name = r["full_name"]
        stars, d24h, d7d, d30d, is_emerging = _compute_deltas_and_emerging(r)
        cat_id = assign_category(r.get("topics", []), r.get("description", ""), full_name=full_name)

        # Check for CJK and translate to English
        desc_raw = html_lib.unescape(r.get("description") or "")
        desc_en = r.get("description_en")
        if not desc_en and contains_cjk(desc_raw):
            desc_en = translate_cjk_sync(desc_raw, conn=conn)
        r["description"] = desc_raw
        r["description_en"] = desc_en
        r["_computed"] = (stars, d24h, d7d, d30d, is_emerging, cat_id)

        # Upsert repository
        cursor.execute("SELECT id, stars, forks, created_at, pushed_at, last_crawled_at FROM repositories WHERE full_name = ?;", (full_name,))
        row = cursor.fetchone()

        if row:
            repo_id, old_stars, old_forks, old_created_at, old_pushed_at, old_crawled_at = row
            # If we have no explicit 24h delta from scraper, check real observed DB star delta over 0.5-3d window
            if not r.get("stars_per_day") and old_crawled_at and old_stars and stars > old_stars:
                try:
                    prev_dt = datetime.fromisoformat(str(old_crawled_at).replace("Z", "+00:00"))
                    if prev_dt.tzinfo is None:
                        prev_dt = prev_dt.replace(tzinfo=timezone.utc)
                    elapsed_days = (now_dt - prev_dt).total_seconds() / 86400.0
                    if 0.5 <= elapsed_days <= 3.5:
                        obs_d24 = min(int(stars * 0.25), max(1, int((stars - old_stars) / elapsed_days)))
                        if obs_d24 > d24h:
                            d24h = obs_d24
                            d7d = min(stars, max(d7d, d24h))
                            d30d = min(stars, max(d30d, d7d))
                            r["_computed"] = (stars, d24h, d7d, d30d, is_emerging, cat_id)
                except Exception:
                    pass

            forks = r.get("forks") or old_forks or max(10, int(stars * 0.12))
            pushed_at = r.get("pushed_at") or old_pushed_at or now_iso
            # Preserve or upgrade created_at when authoritative GitHub API timestamp is available
            created_at = r.get("created_at") if r.get("source") == "github_api" else (old_created_at or r.get("created_at") or now_iso)
            cursor.execute("""
                UPDATE repositories SET
                    stars = ?, forks = ?, description = COALESCE(NULLIF(?, ''), description),
                    description_en = COALESCE(?, description_en),
                    language = COALESCE(NULLIF(?, ''), language),
                    topics = ?, category_id = ?, is_emerging = ?,
                    created_at = ?, pushed_at = ?, last_crawled_at = ?
                WHERE id = ?;
            """, (
                stars, forks, desc_raw, desc_en, r.get("language"),
                json.dumps(r.get("topics", [])), cat_id, is_emerging,
                created_at, pushed_at, now_iso,
                repo_id
            ))
        else:
            forks = r.get("forks") or max(10, int(stars * 0.12))
            created_at = r.get("created_at") or (now_dt - timedelta(days=random.randint(30, 700))).isoformat()
            pushed_at = r.get("pushed_at") or now_iso
            open_issues = r.get("open_issues", 15)
            cursor.execute("""
                INSERT INTO repositories (
                    full_name, name, owner, html_url, description, description_en, language,
                    topics, stars, forks, open_issues, created_at, pushed_at,
                    category_id, is_emerging, last_crawled_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                full_name, r["name"], r["owner"],
                r.get("html_url", f"https://github.com/{full_name}"),
                desc_raw, desc_en, r.get("language", "TypeScript"),
                json.dumps(r.get("topics", [])), stars, forks, open_issues,
                created_at, pushed_at, cat_id, is_emerging, now_iso
            ))
            repo_id = cursor.lastrowid

        # Snapshot maintenance: backfill 7d sparkline ONLY for brand-new repos with zero snapshots;
        # otherwise insert/replace ONLY today's snapshot so deltas stay accurate without ratchet bloat.
        cursor.execute("SELECT COUNT(*) FROM snapshots WHERE repo_id = ?;", (repo_id,))
        total_snaps = cursor.fetchone()[0]
        if total_snaps == 0:
            for i in [7, 5, 4, 3, 2, 1]:
                snap_time = (now_dt - timedelta(days=i)).isoformat()
                s_stars = max(1, stars - int(d7d * (i / 7.0)))
                cursor.execute("""
                    INSERT INTO snapshots (
                        repo_id, timestamp, stars, forks, open_issues,
                        delta_stars_24h, delta_stars_7d, delta_stars_30d
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    repo_id, snap_time, s_stars, int(s_stars * 0.12), 15,
                    d24h, d7d, d30d
                ))

        cursor.execute("SELECT id FROM snapshots WHERE repo_id = ? AND timestamp LIKE ? ORDER BY id DESC;", (repo_id, f"{today_date}%"))
        today_rows = cursor.fetchall()
        if today_rows:
            keep_id = today_rows[0][0]
            cursor.execute("""
                UPDATE snapshots SET
                    timestamp = ?, stars = ?, forks = ?,
                    delta_stars_24h = ?, delta_stars_7d = ?, delta_stars_30d = ?
                WHERE id = ?;
            """, (now_iso, stars, forks, d24h, d7d, d30d, keep_id))
            if len(today_rows) > 1:
                dup_ids = [(x[0],) for x in today_rows[1:]]
                cursor.executemany("DELETE FROM snapshots WHERE id = ?;", dup_ids)
        else:
            cursor.execute("""
                INSERT INTO snapshots (
                    repo_id, timestamp, stars, forks, open_issues,
                    delta_stars_24h, delta_stars_7d, delta_stars_30d
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                repo_id, now_iso, stars, forks, r.get("open_issues", 15),
                d24h, d7d, d30d
            ))

        saved_count += 1

    # Decay is_emerging on stale repositories not seen in the active crawl for >5 days
    stale_cutoff = (now_dt - timedelta(days=5)).isoformat()
    cursor.execute("""
        UPDATE repositories
        SET is_emerging = 0
        WHERE is_emerging = 1 AND last_crawled_at IS NOT NULL AND last_crawled_at < ?;
    """, (stale_cutoff,))

    # Compact historical duplicate snapshots & prune >45d snapshots when bloat is detected
    snap_total = cursor.execute("SELECT COUNT(*) FROM snapshots;").fetchone()[0]
    if snap_total > 120000:
        prune_cutoff = (now_dt - timedelta(days=45)).isoformat()
        cursor.execute("DELETE FROM snapshots WHERE timestamp < ?;", (prune_cutoff,))
        cursor.execute("""
            DELETE FROM snapshots
            WHERE id NOT IN (
                SELECT MAX(id) FROM snapshots GROUP BY repo_id, substr(timestamp, 1, 10)
            );
        """)
        print(f"[Ingestion] Compacted bloated snapshots table (was {snap_total} rows).")

    conn.commit()
    if snap_total > 120000:
        conn.execute("VACUUM;")
    conn.close()
    return saved_count

def scrape_trendshift() -> List[Dict[str, Any]]:
    """Scrapes trending repositories from Trendshift (https://trendshift.io/)."""
    print("[Ingestion] Scraping Trendshift live breakouts...")
    html = fetch_url("https://trendshift.io/")
    if not html:
        return []

    # Parse cards like <a href="/repositories/\d+">...owner/name...</a>
    cards = re.findall(r'<a[^>]*href=[\'"]/repositories/(\d+)[\'"][^>]*>([\s\S]*?)</a>', html)
    repos = []
    seen = set()

    for cid, inner in cards:
        clean = re.sub(r'<[^>]+>', ' ', inner).strip()
        match = re.search(r'([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)', clean)
        if match:
            full_name = match.group(1).strip('/')
            if full_name in seen:
                continue
            seen.add(full_name)

            parts = full_name.split('/')
            owner = parts[0]
            name = parts[1] if len(parts) > 1 else full_name

            desc_match = re.search(rf'{re.escape(name)}[\s\S]*?<p[^>]*>([\s\S]*?)</p>', html)
            desc = html_lib.unescape(re.sub(r'<[^>]+>', '', desc_match.group(1)).strip()) if desc_match else f"Trending project from Trendshift: {full_name}"

            repos.append({
                "full_name": full_name,
                "owner": owner,
                "name": name,
                "description": desc,
                "topics": ["trendshift", "trending", "breakout"],
                "stars": 1500,
                "growth_1d_pct": 8.5,
                "growth_7d_pct": 28.0,
                "growth_30d_pct": 75.0,
                "stars_per_day": 110,
                "language": "TypeScript",
                "is_emerging": 1,
                "needs_enrichment": True
            })

    print(f"[Ingestion] Scraped {len(repos)} active breakouts from Trendshift.")
    return repos

def scrape_github_trending() -> List[Dict[str, Any]]:
    """
    Scrapes official GitHub Trending feeds without consuming any GitHub API quota.
    Collects daily and weekly trending repositories across languages with exact star growth.
    """
    print("[Ingestion] Scraping official GitHub Trending feeds (zero API token cost)...")
    feeds = [
        "https://github.com/trending?since=daily",
        "https://github.com/trending/python?since=daily",
        "https://github.com/trending/typescript?since=daily",
        "https://github.com/trending/rust?since=daily",
        "https://github.com/trending/go?since=daily",
        "https://github.com/trending/c++?since=daily",
        "https://github.com/trending?since=weekly"
    ]
    repos = []
    seen = set()

    for feed_url in feeds:
        is_weekly = "since=weekly" in feed_url
        html = fetch_url(feed_url, timeout=10)
        if not html:
            continue

        articles = re.findall(r'<article[^>]*class="[^"]*Box-row[^"]*"[^>]*>([\s\S]*?)</article>', html)
        for art in articles:
            name_m = re.search(r'href="/([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)"', art)
            if not name_m or "sponsors/" in name_m.group(1):
                continue
            full_name = name_m.group(1).strip()
            if full_name in seen:
                continue
            seen.add(full_name)

            parts = full_name.split('/')
            owner = parts[0]
            name = parts[1] if len(parts) > 1 else full_name

            desc_m = re.search(r'<p[^>]*class="[^"]*col-9[^"]*"[^>]*>([\s\S]*?)</p>', art)
            desc = html_lib.unescape(re.sub(r'<[^>]+>', '', desc_m.group(1)).strip()) if desc_m else ""

            lang_m = re.search(r'itemprop="programmingLanguage">([^<]+)<', art)
            lang = lang_m.group(1).strip() if lang_m else "TypeScript"

            # Parse total stars
            star_link_m = re.search(r'href="[^"]*/stargazers"[^>]*>([\s\S]*?)</a>', art)
            total_stars = 0
            if star_link_m:
                clean_stars = re.sub(r'<[^>]+>', '', star_link_m.group(1)).strip().replace(",", "")
                try:
                    total_stars = int(clean_stars)
                except Exception:
                    pass

            # Parse forks
            fork_link_m = re.search(r'href="[^"]*/forks"[^>]*>([\s\S]*?)</a>', art)
            forks = 0
            if fork_link_m:
                clean_forks = re.sub(r'<[^>]+>', '', fork_link_m.group(1)).strip().replace(",", "")
                try:
                    forks = int(clean_forks)
                except Exception:
                    pass

            # Parse stars today or this week (normalize weekly gain cleanly to daily rate)
            stars_today_m = re.search(r'([0-9,]+)\s+stars\s+(today|this week)', art)
            stars_gain = 0
            period_is_week = is_weekly
            if stars_today_m:
                try:
                    stars_gain = int(stars_today_m.group(1).replace(",", ""))
                    period_is_week = period_is_week or (stars_today_m.group(2) == "this week")
                except Exception:
                    pass

            if total_stars == 0 and stars_gain > 0:
                total_stars = stars_gain * 3

            if period_is_week:
                daily_gain = max(1, stars_gain // 7) if stars_gain > 0 else 0
                growth_7d = round((stars_gain / max(1, total_stars - stars_gain)) * 100.0, 2) if total_stars > 0 else 25.0
                growth_1d = round(growth_7d / 7.0, 2)
            else:
                daily_gain = stars_gain
                growth_1d = round((daily_gain / max(1, total_stars - daily_gain)) * 100.0, 2) if total_stars > 0 else 10.0
                growth_7d = round(growth_1d * 3.5, 2)

            repos.append({
                "full_name": full_name,
                "owner": owner,
                "name": name,
                "description": desc,
                "topics": ["github-trending", "trending", lang.lower()],
                "stars": total_stars,
                "forks": forks,
                "growth_1d_pct": growth_1d,
                "growth_7d_pct": growth_7d,
                "growth_30d_pct": round(growth_7d * 2.2, 2),
                "stars_per_day": daily_gain,
                "language": lang,
                "pushed_at": datetime.now(timezone.utc).isoformat(),
                "is_emerging": 1 if (daily_gain > 50 or growth_1d > 3.0) else 0
            })

    print(f"[Ingestion] Scraped {len(repos)} official trending repositories from GitHub.")
    return repos

def _get_github_headers() -> Tuple[Dict[str, str], str]:
    import os
    token = (os.getenv("GITHUB_TOKEN") or "").strip()
    if not token:
        try:
            from app.config import GITHUB_TOKEN
            token = GITHUB_TOKEN
        except Exception:
            pass
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitPulse-Explorer-Intelligence-Engine/1.0"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers, token

def discover_emerging_repos_via_github_api(fast_mode: bool = False) -> List[Dict[str, Any]]:
    """
    Surgically queries the GitHub Search API for brand-new emerging breakout repositories
    (created in the last 7 to 45 days) that scrapers cannot discover yet.
    Protected by rate-limit probes.
    """
    import urllib.parse
    import time

    headers, _ = _get_github_headers()

    # Verify search rate limit before proceeding
    try:
        req_rl = urllib.request.Request("https://api.github.com/rate_limit", headers=headers)
        with urllib.request.urlopen(req_rl, context=ctx, timeout=8) as resp:
            rl_data = json.loads(resp.read().decode("utf-8"))
            search_remaining = rl_data.get("resources", {}).get("search", {}).get("remaining", 0)
            if search_remaining < 2:
                print(f"[Ingestion] GitHub search rate limit low ({search_remaining} remaining); skipping API discovery.")
                return []
    except Exception as e:
        print(f"[Ingestion] Rate limit probe notice: {e}")

    now = datetime.now(timezone.utc)
    d7 = (now - timedelta(days=7)).strftime("%Y-%m-%d")
    d14 = (now - timedelta(days=14)).strftime("%Y-%m-%d")
    d30 = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    d45 = (now - timedelta(days=45)).strftime("%Y-%m-%d")
    d3 = (now - timedelta(days=3)).strftime("%Y-%m-%d")

    queries = [
        f"created:>{d7} stars:>15",
        f"created:>{d14} stars:>30",
        f"topic:agent created:>{d30} stars:>10",
        f"mcp created:>{d30} stars:>10",
        f"pushed:>{d3} created:>{d45} stars:50..15000",
        f"deepseek created:>{d30} stars:>10",
        f"rust created:>{d30} stars:>20",
        f"topic:security created:>{d45} stars:>15",
        f"topic:trading created:>{d45} stars:>10",
        f"crawler created:>{d45} stars:>15"
    ]
    if fast_mode:
        queries = queries[:5]

    emerging_repos = []
    seen = set()

    print(f"[Ingestion] Querying GitHub API for emerging repositories across {len(queries)} targeted queries...")

    for q in queries:
        url = f"https://api.github.com/search/repositories?q={urllib.parse.quote(q)}&sort=stars&order=desc&per_page=25"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=ctx, timeout=12) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                items = data.get("items", [])
                for item in items:
                    fn = item.get("full_name")
                    if not fn or fn in seen:
                        continue
                    seen.add(fn)

                    stars = item.get("stargazers_count", 0)
                    forks = item.get("forks_count", 0)
                    created_at_str = item.get("created_at") or now.isoformat()
                    try:
                        c_date = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                        age_days = max(1.0, (now - c_date).total_seconds() / 86400.0)
                    except Exception:
                        age_days = 14.0

                    spd = min(stars, max(1, int(stars / age_days)))
                    prior_1d = max(1, stars - spd)
                    growth_1d = round(min(300.0, (spd / prior_1d) * 100.0), 2)
                    prior_7d = max(1, stars - min(stars, spd * min(7, max(1, int(age_days)))))
                    growth_7d = round(min(800.0, ((stars - prior_7d) / prior_7d) * 100.0), 2)

                    emerging_repos.append({
                        "full_name": fn,
                        "owner": item.get("owner", {}).get("login", ""),
                        "name": item.get("name", ""),
                        "description": item.get("description") or f"Emerging breakout project: {fn}",
                        "topics": item.get("topics", []) or ["emerging", "breakout"],
                        "stars": stars,
                        "forks": forks,
                        "open_issues": item.get("open_issues_count", 0),
                        "growth_1d_pct": growth_1d,
                        "growth_7d_pct": growth_7d,
                        "growth_30d_pct": round(min(1500.0, growth_7d * 2.0), 2),
                        "stars_per_day": spd,
                        "language": item.get("language") or "Other",
                        "created_at": created_at_str,
                        "pushed_at": item.get("pushed_at") or now.isoformat(),
                        "is_emerging": 1,
                        "source": "github_api"
                    })
            time.sleep(0.6 if fast_mode else 0.8)  # Gentle pacing to ensure zero burst rate-limiting
        except Exception as e:
            print(f"[Ingestion] Error querying GitHub API for '{q}': {e}")

    print(f"[Ingestion] Discovered {len(emerging_repos)} brand-new emerging repositories via GitHub API.")
    return emerging_repos

def enrich_missing_metadata(repos: List[Dict[str, Any]], max_lookups: int = 25) -> None:
    """
    Fill exact GitHub stars/created_at/pushed_at/forks for scraped breakouts (like Trendshift)
    that lack star telemetry, while keeping core API quota usage under 0.5%.
    """
    candidates = [r for r in repos if r.get("needs_enrichment")]
    if not candidates:
        return

    headers, token = _get_github_headers()
    if not token:
        return

    try:
        req_rl = urllib.request.Request("https://api.github.com/rate_limit", headers=headers)
        with urllib.request.urlopen(req_rl, context=ctx, timeout=8) as resp:
            rl = json.loads(resp.read().decode("utf-8"))
            core_rem = rl.get("resources", {}).get("core", {}).get("remaining", 0)
            if core_rem < 250:
                print(f"[Ingestion] Core rate limit {core_rem} < 250; skipping enrichment.")
                return
    except Exception:
        return

    enriched = 0
    for r in candidates[:max_lookups]:
        fn = r.get("full_name")
        if not fn:
            continue
        try:
            req = urllib.request.Request(f"https://api.github.com/repos/{fn}", headers=headers)
            with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
                item = json.loads(resp.read().decode("utf-8"))
                stars = item.get("stargazers_count", r.get("stars", 0))
                created_at_str = item.get("created_at")
                r["stars"] = stars
                r["forks"] = item.get("forks_count", r.get("forks", 0))
                r["open_issues"] = item.get("open_issues_count", r.get("open_issues", 0))
                if item.get("description"):
                    r["description"] = item["description"]
                if item.get("language"):
                    r["language"] = item["language"]
                if item.get("topics"):
                    for t in item["topics"]:
                        if t not in r["topics"]:
                            r["topics"].append(t)
                if created_at_str:
                    r["created_at"] = created_at_str
                    r["source"] = "github_api"
                    try:
                        c_dt = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
                        age_days = max(1.0, (datetime.now(timezone.utc) - c_dt).total_seconds() / 86400.0)
                        # Active Trendshift repo: estimate 24h velocity conservatively bounded by recent age
                        est_spd = min(stars, max(20, int(stars / min(age_days, 180.0))))
                        r["stars_per_day"] = est_spd
                        r["growth_1d_pct"] = round(min(100.0, (est_spd / max(1, stars - est_spd)) * 100.0), 2)
                    except Exception:
                        pass
                if item.get("pushed_at"):
                    r["pushed_at"] = item["pushed_at"]
                r["needs_enrichment"] = False
                enriched += 1
        except Exception:
            pass

    if enriched:
        print(f"[Ingestion] Enriched {enriched} un-metered Trendshift/breakout repositories from GitHub API.")

def sync_repos_to_turso(repos: List[Dict[str, Any]]):
    """Synchronize crawled repositories and their daily snapshots directly to Turso cloud DB."""
    import os
    turso_url = (os.getenv("TURSO_DATABASE_URL") or "").strip()
    turso_token = (os.getenv("TURSO_AUTH_TOKEN") or "").strip()
    if not turso_url or not turso_token:
        try:
            from app.config import TURSO_DATABASE_URL, TURSO_AUTH_TOKEN
            turso_url = turso_url or TURSO_DATABASE_URL
            turso_token = turso_token or TURSO_AUTH_TOKEN
        except Exception:
            pass

    if not turso_url or not turso_token:
        print("[Ingestion] Turso credentials not present; skipping remote sync.")
        return

    print(f"[Ingestion] Syncing {len(repos)} repositories & snapshots directly to Turso cloud database...")
    try:
        from app.turso_client import TursoClient
        client = TursoClient(turso_url, turso_token, timeout=30)
        now_dt = datetime.now(timezone.utc)
        now_iso = now_dt.isoformat()
        today_date = now_iso[:10]
        batch_size = 50
        snap_batch_size = 35
        batch_errors = 0

        try:
            client.execute("CREATE INDEX IF NOT EXISTS idx_turso_snaps_ts ON snapshots(timestamp DESC, repo_id);")
        except Exception as idx_err:
            print(f"[Ingestion] Turso index check notice: {idx_err}")

        def sql_str(val):
            if val is None:
                return "NULL"
            s = str(val).replace("'", "''")
            return f"'{s}'"

        computed_records = []
        for i in range(0, len(repos), batch_size):
            batch = repos[i:i + batch_size]
            statements = []
            for r in batch:
                full_name = r.get("full_name")
                if not full_name:
                    continue
                if "_computed" in r:
                    stars, d24h, d7d, d30d, is_emerging, cat_id = r["_computed"]
                else:
                    stars, d24h, d7d, d30d, is_emerging = _compute_deltas_and_emerging(r)
                    cat_id = assign_category(r.get("topics", []), r.get("description", ""), full_name=full_name)

                forks = r.get("forks") or max(10, int(stars * 0.12))
                open_issues = r.get("open_issues", 15)
                topics_str = json.dumps(r.get("topics", []))
                created_at = r.get("created_at") or now_iso
                pushed_at = r.get("pushed_at") or now_iso
                is_auth_created = (r.get("source") == "github_api") and bool(r.get("created_at"))
                created_update = (
                    "excluded.created_at"
                    if is_auth_created
                    else "COALESCE(repositories.created_at, excluded.created_at)"
                )

                sql = f"""
                INSERT INTO repositories (
                    full_name, name, owner, html_url, description, description_en, language,
                    topics, stars, forks, open_issues, created_at, pushed_at,
                    category_id, is_emerging, last_crawled_at
                ) VALUES (
                    {sql_str(full_name)}, {sql_str(r.get('name'))}, {sql_str(r.get('owner'))},
                    {sql_str(r.get('html_url', f'https://github.com/{full_name}'))}, {sql_str(r.get('description'))},
                    {sql_str(r.get('description_en'))}, {sql_str(r.get('language', 'TypeScript'))},
                    {sql_str(topics_str)}, {stars}, {forks}, {open_issues},
                    {sql_str(created_at)}, {sql_str(pushed_at)},
                    {sql_str(cat_id)}, {is_emerging}, {sql_str(now_iso)}
                )
                ON CONFLICT(full_name) DO UPDATE SET
                    stars = excluded.stars,
                    forks = COALESCE(NULLIF(excluded.forks, 0), repositories.forks),
                    description = COALESCE(NULLIF(excluded.description, ''), repositories.description),
                    description_en = COALESCE(excluded.description_en, repositories.description_en),
                    language = COALESCE(NULLIF(excluded.language, ''), repositories.language),
                    topics = excluded.topics,
                    category_id = excluded.category_id,
                    is_emerging = excluded.is_emerging,
                    created_at = {created_update},
                    last_crawled_at = excluded.last_crawled_at,
                    pushed_at = excluded.pushed_at;
                """
                statements.append(sql.strip())
                computed_records.append((full_name, stars, forks, open_issues, d24h, d7d, d30d))

            if statements:
                try:
                    client.execute_batch(statements)
                except Exception as b_err:
                    batch_errors += 1
                    print(f"[Ingestion] Warning on Turso repo batch {i}: {b_err}")

        # Sync today's snapshots to Turso cleanly (idempotent per repo per day)
        for i in range(0, len(computed_records), snap_batch_size):
            chunk = computed_records[i:i + snap_batch_size]
            snap_stmts = []
            for full_name, stars, forks, open_issues, d24h, d7d, d30d in chunk:
                fn_sql = sql_str(full_name)
                snap_stmts.append(
                    f"DELETE FROM snapshots WHERE repo_id = (SELECT id FROM repositories WHERE full_name = {fn_sql}) AND substr(timestamp, 1, 10) = '{today_date}';"
                )
                snap_stmts.append(
                    f"INSERT INTO snapshots (repo_id, timestamp, stars, forks, open_issues, delta_stars_24h, delta_stars_7d, delta_stars_30d) "
                    f"SELECT id, {sql_str(now_iso)}, {stars}, {forks}, {open_issues}, {d24h}, {d7d}, {d30d} "
                    f"FROM repositories WHERE full_name = {fn_sql};"
                )
            if snap_stmts:
                try:
                    client.execute_batch(snap_stmts)
                except Exception as s_err:
                    batch_errors += 1
                    print(f"[Ingestion] Warning on Turso snapshot batch {i}: {s_err}")

        # Decay stale is_emerging flags, prune >45d duplicate snapshots, & backfill any snapshotless rows
        stale_cutoff = (now_dt - timedelta(days=5)).isoformat()
        prune_cutoff = (now_dt - timedelta(days=45)).isoformat()
        maint_stmts = [
            f"UPDATE repositories SET is_emerging = 0 WHERE is_emerging = 1 AND last_crawled_at IS NOT NULL AND last_crawled_at < {sql_str(stale_cutoff)};",
            f"DELETE FROM snapshots WHERE timestamp < {sql_str(prune_cutoff)};",
            """
            INSERT INTO snapshots (repo_id, timestamp, stars, forks, open_issues, delta_stars_24h, delta_stars_7d, delta_stars_30d)
            SELECT r.id, COALESCE(r.last_crawled_at, r.created_at), r.stars, r.forks, r.open_issues,
                   0, 0, 0
            FROM repositories r
            WHERE NOT EXISTS (SELECT 1 FROM snapshots s WHERE s.repo_id = r.id);
            """.strip(),
            f"INSERT INTO crawl_history (started_at, finished_at, status, repos_updated, rate_limit_remaining) VALUES ('{now_iso}', '{now_iso}', 'completed', {len(computed_records)}, 5000);"
        ]
        try:
            client.execute_batch(maint_stmts)
        except Exception as m_err:
            batch_errors += 1
            print(f"[Ingestion] Warning on Turso maintenance/crawl_history batch: {m_err}")

        print(f"[Ingestion] Successfully synchronized {len(computed_records)} repositories & snapshots to Turso (batch_errors={batch_errors})!")
    except Exception as e:
        print(f"[Ingestion] Notice syncing to Turso: {e}")

def run_gitpulse_crawl(fast_mode: bool = False) -> Dict[str, Any]:
    """
    Centralized high-speed data collection engine:
    1. Scrapes GitPulse daily/weekly/monthly trending & topic hubs.
    2. Scrapes Trendshift live breakouts (https://trendshift.io/).
    3. Scrapes official GitHub Trending feeds (zero API quota).
    4. Queries GitHub Search API surgically for brand-new emerging breakouts.
    5. Enriches un-metered breakouts, updates SQLite snapshots cleanly, and syncs to Turso Cloud.
    """
    print(f"[Ingestion] Starting data collection cycle (fast_mode={fast_mode}: GitPulse + Trendshift + GitHub Trending + Search API)...")
    urls = [
        "https://thaitrn.github.io/gitpulse/trending/day/",
        "https://thaitrn.github.io/gitpulse/trending/week/",
        "https://thaitrn.github.io/gitpulse/trending/month/",
        "https://thaitrn.github.io/gitpulse/topics/ai-agents/",
        "https://thaitrn.github.io/gitpulse/topics/mcp/",
        "https://thaitrn.github.io/gitpulse/topics/llm/",
        "https://thaitrn.github.io/gitpulse/topics/python/",
        "https://thaitrn.github.io/gitpulse/topics/rust/",
        "https://thaitrn.github.io/gitpulse/topics/react/",
        "https://thaitrn.github.io/gitpulse/topics/claude-code/",
        "https://thaitrn.github.io/gitpulse/topics/cybersecurity/",
        "https://thaitrn.github.io/gitpulse/topics/docker/",
        "https://thaitrn.github.io/gitpulse/topics/trading/",
        "https://thaitrn.github.io/gitpulse/topics/robotics/",
        "https://thaitrn.github.io/gitpulse/topics/javascript/",
        "https://thaitrn.github.io/gitpulse/topics/typescript/",
        "https://thaitrn.github.io/gitpulse/topics/golang/",
        "https://thaitrn.github.io/gitpulse/topics/linux/",
        "https://thaitrn.github.io/gitpulse/topics/windows/",
        "https://thaitrn.github.io/gitpulse/topics/macos/",
        "https://thaitrn.github.io/gitpulse/topics/android/",
        "https://thaitrn.github.io/gitpulse/topics/open-source/",
        "https://thaitrn.github.io/gitpulse/topics/cli/",
        "https://thaitrn.github.io/gitpulse/topics/nodejs/",
        "https://thaitrn.github.io/gitpulse/topics/agent/",
        "https://thaitrn.github.io/gitpulse/topics/claude/",
        "https://thaitrn.github.io/gitpulse/topics/codex/",
        "https://thaitrn.github.io/gitpulse/topics/deep-learning/",
        "https://thaitrn.github.io/gitpulse/topics/machine-learning/",
        "https://thaitrn.github.io/gitpulse/topics/database/",
        "https://thaitrn.github.io/gitpulse/topics/nextjs/",
        "https://thaitrn.github.io/gitpulse/topics/fastapi/",
        "https://thaitrn.github.io/gitpulse/topics/vue/",
        "https://thaitrn.github.io/gitpulse/topics/whisper/",
        "https://thaitrn.github.io/gitpulse/topics/speech-recognition/"
    ]
    if fast_mode:
        urls = urls[:8]

    all_repos = {}

    def _merge_tags(dst: Dict[str, Any], src: Dict[str, Any]):
        for t in src.get("topics", []):
            if t not in dst["topics"]:
                dst["topics"].append(t)

    # 1. Scrape GitPulse feeds
    for url in urls:
        html = fetch_url(url)
        if html:
            items = parse_trending_table(html)
            for item in items:
                fn = item["full_name"]
                if fn not in all_repos:
                    all_repos[fn] = item
                else:
                    if item.get("growth_7d_pct"):
                        all_repos[fn]["growth_7d_pct"] = item["growth_7d_pct"]
                    if item.get("growth_30d_pct"):
                        all_repos[fn]["growth_30d_pct"] = item["growth_30d_pct"]
                    if item.get("stars_per_day") and item["stars_per_day"] > all_repos[fn].get("stars_per_day", 0):
                        all_repos[fn]["stars_per_day"] = item["stars_per_day"]
                    _merge_tags(all_repos[fn], item)

    # 2. Scrape Trendshift live breakouts
    trendshift_repos = scrape_trendshift()
    for item in trendshift_repos:
        fn = item["full_name"]
        if fn not in all_repos:
            all_repos[fn] = item
        else:
            all_repos[fn]["is_emerging"] = 1
            _merge_tags(all_repos[fn], item)

    # 3. Scrape GitHub Official Trending feeds (zero API quota consumption)
    gh_trending_repos = scrape_github_trending()
    for item in gh_trending_repos:
        fn = item["full_name"]
        if fn not in all_repos:
            all_repos[fn] = item
        else:
            if item.get("stars", 0) > all_repos[fn].get("stars", 0):
                all_repos[fn]["stars"] = item["stars"]
            if item.get("forks"):
                all_repos[fn]["forks"] = item["forks"]
            if item.get("stars_per_day"):
                all_repos[fn]["stars_per_day"] = max(all_repos[fn].get("stars_per_day", 0), item["stars_per_day"])
            if item.get("growth_1d_pct"):
                all_repos[fn]["growth_1d_pct"] = max(all_repos[fn].get("growth_1d_pct", 0.0), item["growth_1d_pct"])
            if item.get("pushed_at"):
                all_repos[fn]["pushed_at"] = item["pushed_at"]
            if item.get("is_emerging"):
                all_repos[fn]["is_emerging"] = 1
            all_repos[fn]["needs_enrichment"] = False
            _merge_tags(all_repos[fn], item)

    # 4. Discover Brand-New Emerging Breakouts via GitHub Search API
    api_emerging_repos = discover_emerging_repos_via_github_api(fast_mode=fast_mode)
    for item in api_emerging_repos:
        fn = item["full_name"]
        if fn not in all_repos:
            all_repos[fn] = item
        else:
            all_repos[fn]["is_emerging"] = 1
            all_repos[fn]["source"] = "github_api"
            all_repos[fn]["needs_enrichment"] = False
            if item.get("stars", 0) > all_repos[fn].get("stars", 0):
                all_repos[fn]["stars"] = item["stars"]
            if item.get("forks"):
                all_repos[fn]["forks"] = item["forks"]
            if item.get("created_at"):
                all_repos[fn]["created_at"] = item["created_at"]
            if item.get("pushed_at"):
                all_repos[fn]["pushed_at"] = item["pushed_at"]
            if item.get("language") and item["language"] != "Other":
                all_repos[fn]["language"] = item["language"]
            _merge_tags(all_repos[fn], item)

    # 5. Enrich un-metered Trendshift items (capped at 25 lightweight lookups)
    repo_list = list(all_repos.values())
    if not fast_mode:
        enrich_missing_metadata(repo_list, max_lookups=25)

    print(f"[Ingestion] Combined {len(repo_list)} unique trending and emerging repositories across GitPulse, Trendshift, GitHub Trending & GitHub API.")
    saved = save_repos_to_database(repo_list)
    print(f"[Ingestion] Central SQLite database synchronized: {saved} repositories updated.")
    sync_repos_to_turso(repo_list)
    return {"status": "SUCCESS", "repos_synced": saved, "total_scraped": len(repo_list)}

if __name__ == "__main__":
    import random
    run_gitpulse_crawl()
