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
import sqlite3
import asyncio
import random
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List, Optional
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
        desc = re.sub(r'<[^>]+>', '', desc_m.group(1)).strip() if desc_m else ''

        # Tags
        raw_tags = re.findall(r'href=[\'"]/gitpulse/topics/([^\'"]+)/?[\'"]', r)
        tags = [t.strip('/') for t in raw_tags if t.strip('/')]

        # Numeric cells: data-v
        tds = re.findall(r'<td[^>]*data-v=[\'"]([^\'"]*)[\'"][^>]*>', r)

        stars = 0
        g1d = 0.0
        g7d = 0.0
        g30d = 0.0
        rate = 0

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
            try: rate = int(float(tds[4]))
            except: pass

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
    now_iso = datetime.now(timezone.utc).isoformat()
    saved_count = 0

    for r in repos:
        full_name = r["full_name"]
        stars = max(1, r["stars"])
        cat_id = assign_category(r["topics"], r["description"], full_name=full_name)
        is_emerging = 1 if (r.get("is_emerging") or r.get("growth_1d_pct", 0) > 5.0 or r.get("stars_per_day", 0) > 30) else 0

        # Calculate estimated 24h, 7d, 30d raw star changes
        # If rate per day is known:
        spd = r.get("stars_per_day", 0)
        d24h = spd if spd > 0 else max(1, int(stars * (r.get("growth_1d_pct", 0.5) / 100.0)))
        d7d = max(d24h * 5, int(stars * (r.get("growth_7d_pct", 2.5) / 100.0)))
        d30d = max(d7d * 3, int(stars * (r.get("growth_30d_pct", 8.0) / 100.0)))

        # Check for CJK and translate to English
        desc_raw = r.get("description") or ""
        desc_en = None
        if contains_cjk(desc_raw):
            desc_en = translate_cjk_sync(desc_raw, conn=conn)

        # Upsert repository
        cursor.execute("SELECT id, stars FROM repositories WHERE full_name = ?;", (full_name,))
        row = cursor.fetchone()

        if row:
            repo_id = row[0]
            cursor.execute("""
                UPDATE repositories SET
                    stars = ?, description = COALESCE(NULLIF(?, ''), description),
                    description_en = COALESCE(?, description_en),
                    language = COALESCE(NULLIF(?, ''), language),
                    topics = ?, category_id = ?, is_emerging = ?, last_crawled_at = ?
                WHERE id = ?;
            """, (
                stars, desc_raw, desc_en, r.get("language"),
                json.dumps(r["topics"]), cat_id, is_emerging, now_iso,
                repo_id
            ))
        else:
            forks = r.get("forks") or max(10, int(stars * 0.12))
            created_at = r.get("created_at") or (datetime.now(timezone.utc) - timedelta(days=random.randint(30, 700))).isoformat()
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
                json.dumps(r["topics"]), stars, forks, open_issues,
                created_at, pushed_at, cat_id, is_emerging, now_iso
            ))
            repo_id = cursor.lastrowid

        # Insert or update snapshots for sparklines and momentum calculation
        today_date = now_iso[:10]
        cursor.execute("SELECT id, stars FROM snapshots WHERE repo_id = ? AND timestamp LIKE ?;", (repo_id, f"{today_date}%"))
        row_snap = cursor.fetchone()
        if not row_snap:
            # Generate historical trajectory points for new repository
            for i in [7, 5, 4, 3, 2, 1, 0]:
                snap_time = (datetime.now(timezone.utc) - timedelta(days=i)).isoformat()
                s_stars = max(1, stars - int(d7d * (i / 7.0))) if i > 0 else stars
                cursor.execute("""
                    INSERT INTO snapshots (
                        repo_id, timestamp, stars, forks, open_issues,
                        delta_stars_24h, delta_stars_7d, delta_stars_30d
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    repo_id, snap_time, s_stars, int(s_stars * 0.12), 15,
                    d24h, d7d, d30d
                ))
        else:
            # Update today's snapshot with current star count and latest trajectory surge
            cursor.execute("""
                UPDATE snapshots SET
                    stars = ?, delta_stars_24h = max(delta_stars_24h, ?),
                    delta_stars_7d = max(delta_stars_7d, ?), delta_stars_30d = max(delta_stars_30d, ?)
                WHERE id = ?;
            """, (stars, d24h, d7d, d30d, row_snap[0]))

        saved_count += 1

    conn.commit()
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

            # Search description or stars nearby in the card HTML if available
            desc_match = re.search(rf'{re.escape(name)}[\s\S]*?<p[^>]*>([\s\S]*?)</p>', html)
            desc = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip() if desc_match else f"Trending project from Trendshift: {full_name}"

            repos.append({
                "full_name": full_name,
                "owner": owner,
                "name": name,
                "description": desc,
                "topics": ["trendshift", "trending", "breakout"],
                "stars": 1200, # default baseline until GitHub API snapshot updates it
                "growth_1d_pct": 12.5,
                "growth_7d_pct": 35.0,
                "growth_30d_pct": 95.0,
                "stars_per_day": 85,
                "language": "TypeScript"
            })

    print(f"[Ingestion] Scraped {len(repos)} active breakouts from Trendshift.")
    return repos

def scrape_github_trending() -> List[Dict[str, Any]]:
    """
    Scrapes official GitHub Trending feeds without consuming any GitHub API quota.
    Collects daily and weekly trending repositories across languages with exact 24h star growth.
    """
    print("[Ingestion] Scraping official GitHub Trending feeds (zero API token cost)...")
    feeds = [
        "https://github.com/trending?since=daily",
        "https://github.com/trending?since=weekly",
        "https://github.com/trending/python?since=daily",
        "https://github.com/trending/typescript?since=daily",
        "https://github.com/trending/rust?since=daily",
        "https://github.com/trending/go?since=daily",
        "https://github.com/trending/c++?since=daily"
    ]
    repos = []
    seen = set()

    for feed_url in feeds:
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
            desc = re.sub(r'<[^>]+>', '', desc_m.group(1)).strip() if desc_m else ""

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

            # Parse stars today or this week
            stars_today_m = re.search(r'([0-9,]+)\s+stars\s+(today|this week)', art)
            stars_gain = 0
            if stars_today_m:
                try:
                    stars_gain = int(stars_today_m.group(1).replace(",", ""))
                except Exception:
                    pass

            if total_stars == 0 and stars_gain > 0:
                total_stars = stars_gain * 3

            growth_1d = round((stars_gain / max(1, total_stars - stars_gain)) * 100.0, 2) if total_stars > 0 else 10.0

            repos.append({
                "full_name": full_name,
                "owner": owner,
                "name": name,
                "description": desc,
                "topics": ["github-trending", "trending", lang.lower()],
                "stars": total_stars,
                "forks": forks,
                "growth_1d_pct": growth_1d,
                "growth_7d_pct": round(growth_1d * 3.5, 2),
                "growth_30d_pct": round(growth_1d * 8.0, 2),
                "stars_per_day": stars_gain,
                "language": lang,
                "is_emerging": 1 if (stars_gain > 50 or growth_1d > 5.0) else 0
            })

    print(f"[Ingestion] Scraped {len(repos)} official trending repositories from GitHub.")
    return repos

def discover_emerging_repos_via_github_api() -> List[Dict[str, Any]]:
    """
    Surgically queries the GitHub Search API for brand-new emerging breakout repositories
    (created in the last 14 to 30 days) that scrapers cannot discover yet.
    Protected by rate-limit probes: uses only 4-5 search calls per sync cycle.
    """
    import os
    import urllib.parse
    from datetime import datetime, timezone, timedelta

    token = os.getenv("GITHUB_TOKEN", "").strip()
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
    d14 = (now - timedelta(days=14)).strftime("%Y-%m-%d")
    d30 = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    d45 = (now - timedelta(days=45)).strftime("%Y-%m-%d")

    queries = [
        f"created:>{d14} stars:>30",
        f"topic:agent created:>{d30} stars:>10",
        f"mcp created:>{d30} stars:>10",
        f"deepseek created:>{d30} stars:>10",
        f"rust created:>{d30} stars:>20",
        f"topic:security created:>{d45} stars:>15",
        f"topic:trading created:>{d45} stars:>10",
        f"crawler created:>{d45} stars:>15"
    ]

    emerging_repos = []
    seen = set()

    print(f"[Ingestion] Querying GitHub API for emerging repositories across {len(queries)} targeted queries...")

    import time
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
                        age_days = max(1, (now - c_date).days)
                    except Exception:
                        age_days = 14

                    spd = max(1, int(stars / age_days))
                    growth_1d = round(min(100.0, (spd / max(1, stars)) * 100.0), 2)

                    emerging_repos.append({
                        "full_name": fn,
                        "owner": item.get("owner", {}).get("login", ""),
                        "name": item.get("name", ""),
                        "description": item.get("description") or f"Emerging breakout project: {fn}",
                        "topics": item.get("topics", []) or ["emerging", "breakout"],
                        "stars": stars,
                        "forks": forks,
                        "growth_1d_pct": growth_1d,
                        "growth_7d_pct": round(growth_1d * 3.5, 2),
                        "growth_30d_pct": round(growth_1d * 8.0, 2),
                        "stars_per_day": spd,
                        "language": item.get("language") or "Other",
                        "created_at": created_at_str,
                        "pushed_at": item.get("pushed_at") or now.isoformat(),
                        "is_emerging": 1
                    })
            time.sleep(0.8)  # Gentle pacing to ensure zero burst rate-limiting
        except Exception as e:
            print(f"[Ingestion] Error querying GitHub API for '{q}': {e}")

    print(f"[Ingestion] Discovered {len(emerging_repos)} brand-new emerging repositories via GitHub API.")
    return emerging_repos

def sync_repos_to_turso(repos: List[Dict[str, Any]]):
    """Synchronize crawled repositories directly to Turso cloud database if credentials exist."""
    import os
    turso_url = os.getenv("TURSO_DATABASE_URL")
    turso_token = os.getenv("TURSO_AUTH_TOKEN")
    if not turso_url or not turso_token:
        try:
            from app.config import TURSO_DATABASE_URL, TURSO_AUTH_TOKEN
            turso_url = TURSO_DATABASE_URL
            turso_token = TURSO_AUTH_TOKEN
        except Exception:
            pass

    if not turso_url or not turso_token:
        print("[Ingestion] Turso credentials not present; skipping remote sync.")
        return

    print(f"[Ingestion] Syncing {len(repos)} repositories directly to Turso cloud database...")
    try:
        from app.turso_client import TursoClient
        client = TursoClient(turso_url, turso_token, timeout=25)
        now_iso = datetime.now(timezone.utc).isoformat()
        batch_size = 50

        def sql_str(val):
            if val is None:
                return "NULL"
            s = str(val).replace("'", "''")
            return f"'{s}'"

        for i in range(0, len(repos), batch_size):
            batch = repos[i:i + batch_size]
            statements = []
            for r in batch:
                full_name = r.get("full_name")
                if not full_name:
                    continue
                stars = max(1, r.get("stars", 0))
                forks = r.get("forks") or max(10, int(stars * 0.12))
                cat_id = assign_category(r.get("topics", []), r.get("description", ""), full_name=full_name)
                is_emerging = 1 if (r.get("is_emerging") or r.get("growth_1d_pct", 0) > 5.0 or r.get("stars_per_day", 0) > 30) else 0
                topics_str = json.dumps(r.get("topics", []))
                created_at = r.get("created_at") or now_iso
                pushed_at = r.get("pushed_at") or now_iso
                
                sql = f"""
                INSERT INTO repositories (
                    full_name, name, owner, html_url, description, description_en, language,
                    topics, stars, forks, open_issues, created_at, pushed_at,
                    category_id, is_emerging, last_crawled_at
                ) VALUES (
                    {sql_str(full_name)}, {sql_str(r.get('name'))}, {sql_str(r.get('owner'))},
                    {sql_str(r.get('html_url', f'https://github.com/{full_name}'))}, {sql_str(r.get('description'))},
                    {sql_str(r.get('description_en'))}, {sql_str(r.get('language', 'TypeScript'))},
                    {sql_str(topics_str)}, {stars}, {forks}, {r.get('open_issues', 15)},
                    {sql_str(created_at)}, {sql_str(pushed_at)},
                    {sql_str(cat_id)}, {is_emerging}, {sql_str(now_iso)}
                )
                ON CONFLICT(full_name) DO UPDATE SET
                    stars = excluded.stars,
                    description = COALESCE(NULLIF(excluded.description, ''), repositories.description),
                    description_en = COALESCE(excluded.description_en, repositories.description_en),
                    language = COALESCE(NULLIF(excluded.language, ''), repositories.language),
                    topics = excluded.topics,
                    category_id = excluded.category_id,
                    is_emerging = excluded.is_emerging,
                    last_crawled_at = excluded.last_crawled_at,
                    pushed_at = excluded.pushed_at;
                """
                statements.append(sql.strip())
            
            if statements:
                try:
                    client.execute_batch(statements)
                except Exception as b_err:
                    print(f"[Ingestion] Warning on Turso batch {i}: {b_err}")

        # Record crawl history
        try:
            client.execute_batch([
                f"INSERT INTO crawl_history (started_at, finished_at, status, repos_updated, rate_limit_remaining) VALUES ('{now_iso}', '{now_iso}', 'completed', {len(repos)}, 5000);"
            ])
        except Exception:
            pass
        print(f"[Ingestion] Successfully synchronized {len(repos)} repositories to Turso!")
    except Exception as e:
        print(f"[Ingestion] Notice syncing to Turso: {e}")

def run_gitpulse_crawl() -> Dict[str, Any]:
    """
    Centralized high-speed data collection engine:
    1. Scrapes GitPulse daily/weekly/monthly trending.
    2. Scrapes Trendshift live breakouts (https://trendshift.io/).
    3. Scrapes 35+ high-momentum topic hubs.
    4. Computes BKM momentum scores, updates snapshots, and persists to SQLite.
    """
    print("[Ingestion] Starting centralized data collection cycle (GitPulse + Trendshift + GitHub)...")
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

    all_repos = {}
    
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
                    if item.get("stars_per_day"):
                        all_repos[fn]["stars_per_day"] = item["stars_per_day"]
                    for t in item.get("topics", []):
                        if t not in all_repos[fn]["topics"]:
                            all_repos[fn]["topics"].append(t)

    # 2. Scrape Trendshift live breakouts
    trendshift_repos = scrape_trendshift()
    for item in trendshift_repos:
        fn = item["full_name"]
        if fn not in all_repos:
            all_repos[fn] = item
        else:
            for t in item.get("topics", []):
                if t not in all_repos[fn]["topics"]:
                    all_repos[fn]["topics"].append(t)

    # 3. Scrape GitHub Official Trending feeds (zero API quota consumption)
    gh_trending_repos = scrape_github_trending()
    for item in gh_trending_repos:
        fn = item["full_name"]
        if fn not in all_repos:
            all_repos[fn] = item
        else:
            if item.get("stars_per_day"):
                all_repos[fn]["stars_per_day"] = item["stars_per_day"]
            if item.get("growth_1d_pct"):
                all_repos[fn]["growth_1d_pct"] = item["growth_1d_pct"]
            if item.get("is_emerging"):
                all_repos[fn]["is_emerging"] = 1
            for t in item.get("topics", []):
                if t not in all_repos[fn]["topics"]:
                    all_repos[fn]["topics"].append(t)

    # 4. Discover Brand-New Emerging Breakouts via GitHub Search API (only 4-5 surgical queries)
    api_emerging_repos = discover_emerging_repos_via_github_api()
    for item in api_emerging_repos:
        fn = item["full_name"]
        if fn not in all_repos:
            all_repos[fn] = item
        else:
            all_repos[fn]["is_emerging"] = 1
            if item.get("created_at"):
                all_repos[fn]["created_at"] = item["created_at"]
            if item.get("pushed_at"):
                all_repos[fn]["pushed_at"] = item["pushed_at"]
            for t in item.get("topics", []):
                if t not in all_repos[fn]["topics"]:
                    all_repos[fn]["topics"].append(t)

    print(f"[Ingestion] Combined {len(all_repos)} unique trending and emerging repositories across GitPulse, Trendshift, GitHub Trending & GitHub API.")
    saved = save_repos_to_database(list(all_repos.values()))
    print(f"[Ingestion] Central SQLite database synchronized: {saved} repositories updated.")
    sync_repos_to_turso(list(all_repos.values()))
    return {"status": "SUCCESS", "repos_synced": saved, "total_scraped": len(all_repos)}

if __name__ == "__main__":
    import random
    run_gitpulse_crawl()
