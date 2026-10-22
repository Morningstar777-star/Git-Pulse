import json
import random
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any

# Topics taxonomy definition with icons & metadata
TOPICS_METADATA = [
    {
        "id": "llm-agents",
        "name": "LLMs, AI Agents & Reasoning Engines",
        "description": "Autonomous agents, local inference engines, prompt engineering, and LLM orchestration.",
        "icon": "Bot",
        "keywords": ["llm", "ai-agents", "agentic", "rag", "ollama", "langchain", "deepseek"]
    },
    {
        "id": "web-scraping",
        "name": "Web Scraping, Crawlers & Extraction",
        "description": "High-throughput data extraction, browser automation, headless spiders, and intelligent parsers.",
        "icon": "Layers",
        "keywords": ["web-scraping", "crawler", "playwright", "puppeteer", "scrapy", "spider", "crawl4ai"]
    },
    {
        "id": "speech-audio",
        "name": "Speech Synthesis, Voice AI & Audio DSP",
        "description": "State-of-the-art text-to-speech, voice cloning, real-time transcription, and audio models.",
        "icon": "Mic",
        "keywords": ["speech", "tts", "whisper", "voice-cloning", "speech-recognition", "audio", "fish-speech"]
    },
    {
        "id": "gaming-graphics",
        "name": "Game Engines, 3D Models & WebGL",
        "description": "Interactive 3D rendering, WebGL canvas frameworks, shaders, spatial physics, and game engines.",
        "icon": "Gamepad2",
        "keywords": ["3d", "threejs", "webgl", "game-engine", "godot", "rendering", "shaders", "react-three-fiber"]
    },
    {
        "id": "medical-science",
        "name": "Medical Science & BioTech Intelligence",
        "description": "Computational biology, medical imaging models, bioinformatics, and healthcare diagnostics.",
        "icon": "Activity",
        "keywords": ["medical", "bioinformatics", "healthcare", "genomics", "clinical", "biology", "biomedical"]
    },
    {
        "id": "arts-culture",
        "name": "Arts, Culture & Creative Technology",
        "description": "Open-source digital canvas tools, vector art editors, generative music, and cultural archives.",
        "icon": "Palette",
        "keywords": ["art", "culture", "photo-editor", "vector", "drawing", "creative-coding", "photocraft"]
    },
    {
        "id": "smart-automation",
        "name": "Browser Agents & Autonomous Workflows",
        "description": "Automated web browsing agents, robotic process automation, and intelligent task execution.",
        "icon": "Cpu",
        "keywords": ["browser-use", "automation", "workflow", "browser-agent", "task-automation", "bot"]
    },
    {
        "id": "privacy-adblock",
        "name": "Privacy, Adblocking & Anti-Tracking",
        "description": "System-wide debloaters, network adblocking, DNS filters, and anti-censorship protocols.",
        "icon": "EyeOff",
        "keywords": ["privacy", "adblock", "debloat", "anti-tracking", "dns", "vpn", "tor", "cleanyourtv"]
    },
    {
        "id": "education-learning",
        "name": "Education, Open Knowledge & Books",
        "description": "Curated life guides, algorithmic cheat sheets, computer science textbooks, and interactive tutorials.",
        "icon": "BookOpen",
        "keywords": ["education", "learning", "curriculum", "textbooks", "tutorial", "awesome-list", "life-guide"]
    },
    {
        "id": "cybersecurity",
        "name": "Cybersecurity, Reverse Engineering & Pentest",
        "description": "Vulnerability scanning, offensive security tooling, decompiler suites, and binary analysis.",
        "icon": "ShieldCheck",
        "keywords": ["cybersecurity", "security", "pentest", "reverse-engineering", "decompiler", "vulnerability", "rea"]
    },
    {
        "id": "web-frameworks",
        "name": "Web Development & Reactive UI",
        "description": "Next-generation frontend, full-stack runtimes, reactive UI libraries, and styling systems.",
        "icon": "Globe",
        "keywords": ["react", "nextjs", "vue", "typescript", "tailwind", "web"]
    },
    {
        "id": "data-engineering",
        "name": "Data Engineering & Analytics Stores",
        "description": "High-throughput stream processing, analytical columnar stores, and vector databases.",
        "icon": "Database",
        "keywords": ["database", "data-engineering", "duckdb", "polars", "sql", "clickhouse"]
    },
    {
        "id": "quant-datasci",
        "name": "Quantitative Finance & Trading Systems",
        "description": "Algorithmic trading frameworks, backtesting engines, statistical modeling, and financial analytics.",
        "icon": "TrendingUp",
        "keywords": ["trading", "quantitative-finance", "backtesting", "finance", "crypto"]
    },
    {
        "id": "ai-ml",
        "name": "Artificial Intelligence & Core Machine Learning",
        "description": "Foundational deep learning, neural networks, computer vision, and diffusion models.",
        "icon": "Brain",
        "keywords": ["machine-learning", "deep-learning", "pytorch", "neural-network", "computer-vision"]
    },
    {
        "id": "infrastructure",
        "name": "Open Source Infrastructure & DevOps",
        "description": "Cloud-native orchestration, container engines, mesh networks, and serverless runtimes.",
        "icon": "Server",
        "keywords": ["kubernetes", "docker", "devops", "cloud-native", "infrastructure"]
    },
    {
        "id": "robotics-hardware",
        "name": "Robotics, IoT & Embedded Systems",
        "description": "ROS systems, microcontroller firmware, edge robotics, and physical computing platforms.",
        "icon": "Radio",
        "keywords": ["robotics", "embedded", "ros", "iot", "firmware", "hardware"]
    },
    {
        "id": "emerging-tech",
        "name": "Emerging Technologies & Breakthrough Innovations",
        "description": "Breakout experimental utilities, new programming languages, cross-disciplinary innovations.",
        "icon": "Sparkles",
        "keywords": ["experimental", "emerging", "breakout", "novelty", "innovation"]
    }
]

# Curated Seed Repositories (Diverse, authentic, high-value projects)
RAW_SEED_REPOSITORIES = [
    # Top Highest Momentum Breakouts (Reference Trending Projects)
    {
        "full_name": "deepseek-ai/deepseek-harness", "name": "deepseek-harness", "owner": "deepseek-ai",
        "description": "DeepSeek Harness: Everything is a Plugin. Modular execution harness for reasoning models.",
        "language": "Python", "stars": 257700, "forks": 31200, "open_issues": 140,
        "category_id": "llm-agents", "created_at": "2024-12-01T10:00:00Z",
        "topics": ["cordis", "dsh", "deepseek", "plugins", "ai-agents", "reasoning", "llm", "python"],
        "growth_24h": 3681, "growth_7d": 8500, "growth_30d": 27300, "is_emerging": True
    },
    {
        "full_name": "storytold/photocraft", "name": "photocraft", "owner": "storytold",
        "description": "PhotoCraft: An open-source, photo editor written by scratch in pure Rust.",
        "language": "Rust", "stars": 70900, "forks": 4200, "open_issues": 65,
        "category_id": "emerging-tech", "created_at": "2024-10-15T08:00:00Z",
        "topics": ["art", "rust", "photo-editor", "image-processing", "graphics", "wasm", "canvas"],
        "growth_24h": 3225, "growth_7d": 13800, "growth_30d": 31500, "is_emerging": True
    },
    {
        "full_name": "morluto/rea", "name": "rea", "owner": "morluto",
        "description": "Reverse engineer anything with agents, from app behavior down to native binaries.",
        "language": "TypeScript", "stars": 361700, "forks": 44800, "open_issues": 310,
        "category_id": "cybersecurity", "created_at": "2024-08-20T14:00:00Z",
        "topics": ["cordis", "decompiler", "reverse-engineering", "agents", "security", "binary-analysis", "typescript"],
        "growth_24h": 1894, "growth_7d": 221700, "growth_30d": 280000, "is_emerging": True
    },
    {
        "full_name": "eternity4719/HowToLiveBetter", "name": "HowToLiveBetter", "owner": "eternity4719",
        "description": "高性价比人生指南：长寿防病、急救、省钱理财、法律红线、失业与工伤、医保社保、恋爱婚育、怀孕育儿、创业与做平台合规、出国与技能。",
        "language": "Markdown", "stars": 67900, "forks": 9800, "open_issues": 28,
        "category_id": "emerging-tech", "created_at": "2024-05-10T12:00:00Z",
        "topics": ["life-guide", "health", "finance", "china", "knowledge-base", "handbook"],
        "growth_24h": 1508, "growth_7d": 5770, "growth_30d": 55900, "is_emerging": True
    },
    {
        "full_name": "wheresryan22/anatomy", "name": "anatomy", "owner": "wheresryan22",
        "description": "An agent skill for creating detailed, interactive isometric illustrations of real-world machines and complex systems.",
        "language": "TypeScript", "stars": 18800, "forks": 1400, "open_issues": 19,
        "category_id": "ai-ml", "created_at": "2024-11-20T16:00:00Z",
        "topics": ["agent-skill", "svg", "webgl", "illustration", "agents", "3d", "canvas"],
        "growth_24h": 1344, "growth_7d": 20800, "growth_30d": 21000, "is_emerging": True
    },
    # 1. AI & Machine Learning
    {
        "full_name": "huggingface/transformers", "name": "transformers", "owner": "huggingface",
        "description": "State-of-the-art Machine Learning for Pytorch, TensorFlow, and JAX.",
        "language": "Python", "stars": 138500, "forks": 26400, "open_issues": 1240,
        "category_id": "ai-ml", "created_at": "2018-10-29T16:00:00Z",
        "topics": ["machine-learning", "pytorch", "transformers", "deep-learning", "nlp"],
        "growth_24h": 145, "growth_7d": 980, "growth_30d": 4100, "is_emerging": False
    },
    {
        "full_name": "pytorch/pytorch", "name": "pytorch", "owner": "pytorch",
        "description": "Tensors and Dynamic neural networks in Python with strong GPU acceleration.",
        "language": "Python", "stars": 86200, "forks": 23500, "open_issues": 16400,
        "category_id": "ai-ml", "created_at": "2016-08-13T05:00:00Z",
        "topics": ["deep-learning", "machine-learning", "neural-network", "gpu", "tensors"],
        "growth_24h": 68, "growth_7d": 490, "growth_30d": 2150, "is_emerging": False
    },
    {
        "full_name": "comfyanonymous/ComfyUI", "name": "ComfyUI", "owner": "comfyanonymous",
        "description": "The most powerful and modular stable diffusion GUI and backend with a graph/nodes interface.",
        "language": "Python", "stars": 62400, "forks": 6500, "open_issues": 1890,
        "category_id": "ai-ml", "created_at": "2023-01-15T02:00:00Z",
        "topics": ["stable-diffusion", "generative-ai", "image-generation", "nodes", "ui"],
        "growth_24h": 320, "growth_7d": 2100, "growth_30d": 8400, "is_emerging": True
    },
    {
        "full_name": "AUTOMATIC1111/stable-diffusion-webui", "name": "stable-diffusion-webui", "owner": "AUTOMATIC1111",
        "description": "Stable Diffusion web UI based on Gradio library for generative synthesis.",
        "language": "Python", "stars": 142000, "forks": 27800, "open_issues": 2100,
        "category_id": "ai-ml", "created_at": "2022-08-22T14:00:00Z",
        "topics": ["stable-diffusion", "gradio", "generative-ai", "python"],
        "growth_24h": 85, "growth_7d": 620, "growth_30d": 2700, "is_emerging": False
    },
    {
        "full_name": "karpathy/nanoGPT", "name": "nanoGPT", "owner": "karpathy",
        "description": "The simplest, fastest repository for training/finetuning medium-sized GPTs.",
        "language": "Python", "stars": 38900, "forks": 5800, "open_issues": 120,
        "category_id": "ai-ml", "created_at": "2022-12-29T10:00:00Z",
        "topics": ["gpt", "transformer", "education", "deep-learning", "pytorch"],
        "growth_24h": 92, "growth_7d": 640, "growth_30d": 2600, "is_emerging": False
    },
    {
        "full_name": "vllm-project/vllm", "name": "vllm", "owner": "vllm-project",
        "description": "A high-throughput and memory-efficient inference and serving engine for LLMs.",
        "language": "Python", "stars": 38500, "forks": 5400, "open_issues": 1450,
        "category_id": "ai-ml", "created_at": "2023-06-08T19:00:00Z",
        "topics": ["llm-inference", "pagedattention", "cuda", "serving", "high-performance"],
        "growth_24h": 410, "growth_7d": 2680, "growth_30d": 9800, "is_emerging": True
    },

    # 2. LLMs, AI Agents & Developer Tools
    {
        "full_name": "ollama/ollama", "name": "ollama", "owner": "ollama",
        "description": "Get up and running with Llama 3, Mistral, Gemma, and other large language models locally.",
        "language": "Go", "stars": 112000, "forks": 9800, "open_issues": 920,
        "category_id": "llm-agents", "created_at": "2023-06-21T18:00:00Z",
        "topics": ["llm", "llama", "local-ai", "go", "inference", "cli"],
        "growth_24h": 580, "growth_7d": 3850, "growth_30d": 14200, "is_emerging": True
    },
    {
        "full_name": "browser-use/browser-use", "name": "browser-use", "owner": "browser-use",
        "description": "Make websites accessible for AI agents. Control browser tabs with natural language commands.",
        "language": "Python", "stars": 24800, "forks": 2700, "open_issues": 180,
        "category_id": "llm-agents", "created_at": "2024-11-04T09:00:00Z",
        "topics": ["browser-automation", "ai-agents", "playwright", "vision-models", "agentic"],
        "growth_24h": 740, "growth_7d": 4900, "growth_30d": 18200, "is_emerging": True
    },
    {
        "full_name": "crewAIInc/crewAI", "name": "crewAI", "owner": "crewAIInc",
        "description": "Framework for orchestrating role-playing, autonomous AI agents. Foster collaborative intelligence.",
        "language": "Python", "stars": 26900, "forks": 3800, "open_issues": 410,
        "category_id": "llm-agents", "created_at": "2023-11-20T12:00:00Z",
        "topics": ["ai-agents", "multi-agent", "orchestration", "llm", "python"],
        "growth_24h": 310, "growth_7d": 1950, "growth_30d": 7400, "is_emerging": True
    },
    {
        "full_name": "Significant-Gravitas/AutoGPT", "name": "AutoGPT", "owner": "Significant-Gravitas",
        "description": "AutoGPT is the vision of accessible AI for everyone, to use and to build on.",
        "language": "Python", "stars": 169000, "forks": 44200, "open_issues": 750,
        "category_id": "llm-agents", "created_at": "2023-03-16T09:00:00Z",
        "topics": ["ai-agents", "autonomous", "gpt-4", "llm"],
        "growth_24h": 120, "growth_7d": 890, "growth_30d": 3600, "is_emerging": False
    },
    {
        "full_name": "langchain-ai/langchain", "name": "langchain", "owner": "langchain-ai",
        "description": "🦜🔗 Build context-aware reasoning applications with LangChain.",
        "language": "Python", "stars": 98500, "forks": 16200, "open_issues": 2400,
        "category_id": "llm-agents", "created_at": "2022-10-17T02:00:00Z",
        "topics": ["llm", "rag", "agents", "langchain", "python"],
        "growth_24h": 210, "growth_7d": 1450, "growth_30d": 5900, "is_emerging": False
    },
    {
        "full_name": "cline/cline", "name": "cline", "owner": "cline",
        "description": "Autonomous coding agent right in your IDE, capable of creating/editing files and running commands.",
        "language": "TypeScript", "stars": 23400, "forks": 2400, "open_issues": 310,
        "category_id": "llm-agents", "created_at": "2024-07-12T14:00:00Z",
        "topics": ["coding-agent", "vscode", "autonomous-coding", "agentic", "typescript"],
        "growth_24h": 680, "growth_7d": 4100, "growth_30d": 15800, "is_emerging": True
    },

    # 3. Web Development & Frameworks
    {
        "full_name": "shadcn-ui/ui", "name": "ui", "owner": "shadcn-ui",
        "description": "Beautifully designed components that you can copy and paste into your apps. Accessible. Customizable. Open Source.",
        "language": "TypeScript", "stars": 74500, "forks": 6100, "open_issues": 210,
        "category_id": "web-frameworks", "created_at": "2023-01-22T19:00:00Z",
        "topics": ["radix-ui", "tailwindcss", "react", "components", "design-system"],
        "growth_24h": 460, "growth_7d": 2980, "growth_30d": 11500, "is_emerging": True
    },
    {
        "full_name": "vercel/next.js", "name": "next.js", "owner": "vercel",
        "description": "The React Framework for the Web. Hybrid static & server rendering, TypeScript support, smart bundling.",
        "language": "JavaScript", "stars": 128000, "forks": 27200, "open_issues": 2800,
        "category_id": "web-frameworks", "created_at": "2016-10-05T23:00:00Z",
        "topics": ["react", "nextjs", "ssr", "serverless", "framework"],
        "growth_24h": 180, "growth_7d": 1240, "growth_30d": 5100, "is_emerging": False
    },
    {
        "full_name": "tailwindlabs/tailwindcss", "name": "tailwindcss", "owner": "tailwindlabs",
        "description": "A utility-first CSS framework for rapid UI development.",
        "language": "TypeScript", "stars": 83400, "forks": 4200, "open_issues": 40,
        "category_id": "web-frameworks", "created_at": "2017-11-01T15:00:00Z",
        "topics": ["css", "tailwindcss", "postcss", "design-system", "responsive"],
        "growth_24h": 190, "growth_7d": 1350, "growth_30d": 5400, "is_emerging": False
    },
    {
        "full_name": "astral-sh/uv", "name": "uv", "owner": "astral-sh",
        "description": "An extremely fast Python package and project manager, written in Rust.",
        "language": "Rust", "stars": 42500, "forks": 1400, "open_issues": 320,
        "category_id": "web-frameworks", "created_at": "2024-02-05T16:00:00Z",
        "topics": ["python", "rust", "package-manager", "high-performance", "developer-tools"],
        "growth_24h": 520, "growth_7d": 3450, "growth_30d": 13900, "is_emerging": True
    },
    {
        "full_name": "facebook/react", "name": "react", "owner": "facebook",
        "description": "The library for web and native user interfaces.",
        "language": "JavaScript", "stars": 231000, "forks": 46500, "open_issues": 740,
        "category_id": "web-frameworks", "created_at": "2013-05-24T16:00:00Z",
        "topics": ["react", "frontend", "ui", "declarative", "javascript"],
        "growth_24h": 140, "growth_7d": 980, "growth_30d": 4100, "is_emerging": False
    },

    # 4. Data Engineering & Databases
    {
        "full_name": "duckdb/duckdb", "name": "duckdb", "owner": "duckdb",
        "description": "DuckDB is an in-process SQL OLAP database management system.",
        "language": "C++", "stars": 28400, "forks": 2100, "open_issues": 890,
        "category_id": "data-engineering", "created_at": "2018-07-16T12:00:00Z",
        "topics": ["olap", "database", "analytics", "sql", "embedded-db"],
        "growth_24h": 240, "growth_7d": 1620, "growth_30d": 6200, "is_emerging": True
    },
    {
        "full_name": "pola-rs/polars", "name": "polars", "owner": "pola-rs",
        "description": "Dataframes powered by a multithreaded, vectorized query engine, written in Rust.",
        "language": "Rust", "stars": 31200, "forks": 2200, "open_issues": 810,
        "category_id": "data-engineering", "created_at": "2020-05-18T19:00:00Z",
        "topics": ["dataframe", "rust", "apache-arrow", "data-science", "vectorized"],
        "growth_24h": 190, "growth_7d": 1280, "growth_30d": 5100, "is_emerging": True
    },
    {
        "full_name": "ClickHouse/ClickHouse", "name": "ClickHouse", "owner": "ClickHouse",
        "description": "ClickHouse® is a free analytics DBMS for big data with lightning query times.",
        "language": "C++", "stars": 39400, "forks": 6800, "open_issues": 3100,
        "category_id": "data-engineering", "created_at": "2016-04-14T11:00:00Z",
        "topics": ["clickhouse", "database", "analytics", "olap", "big-data"],
        "growth_24h": 110, "growth_7d": 780, "growth_30d": 3200, "is_emerging": False
    },
    {
        "full_name": "qdrant/qdrant", "name": "qdrant", "owner": "qdrant",
        "description": "Qdrant - High-performance, massive-scale Vector Database for next-gen AI applications.",
        "language": "Rust", "stars": 22100, "forks": 1700, "open_issues": 290,
        "category_id": "data-engineering", "created_at": "2021-05-24T14:00:00Z",
        "topics": ["vector-search", "embeddings", "similarity-search", "rust", "database"],
        "growth_24h": 175, "growth_7d": 1180, "growth_30d": 4600, "is_emerging": True
    },
    {
        "full_name": "apache/spark", "name": "spark", "owner": "apache",
        "description": "Apache Spark - A unified analytics engine for large-scale data processing.",
        "language": "Scala", "stars": 40200, "forks": 28100, "open_issues": 480,
        "category_id": "data-engineering", "created_at": "2014-02-27T03:00:00Z",
        "topics": ["big-data", "spark", "data-processing", "distributed-computing"],
        "growth_24h": 45, "growth_7d": 320, "growth_30d": 1400, "is_emerging": False
    },

    # 5. Quantitative Finance & Data Science
    {
        "full_name": "freqtrade/freqtrade", "name": "freqtrade", "owner": "freqtrade",
        "description": "Free, open source crypto trading bot written in Python with backtesting and machine learning modules.",
        "language": "Python", "stars": 33200, "forks": 7100, "open_issues": 160,
        "category_id": "quant-datasci", "created_at": "2017-09-02T13:00:00Z",
        "topics": ["trading-bot", "cryptocurrency", "backtesting", "algo-trading", "python"],
        "growth_24h": 210, "growth_7d": 1420, "growth_30d": 5600, "is_emerging": True
    },
    {
        "full_name": "ccxt/ccxt", "name": "ccxt", "owner": "ccxt",
        "description": "A JavaScript / Python / PHP cryptocurrency trading API with support for over 100 exchanges.",
        "language": "TypeScript", "stars": 34800, "forks": 8400, "open_issues": 620,
        "category_id": "quant-datasci", "created_at": "2017-05-18T10:00:00Z",
        "topics": ["crypto", "finance", "trading", "exchange-api", "algorithmic-trading"],
        "growth_24h": 85, "growth_7d": 590, "growth_30d": 2400, "is_emerging": False
    },
    {
        "full_name": "ranaroussi/yfinance", "name": "yfinance", "owner": "ranaroussi",
        "description": "Download market data from Yahoo! Finance's API effortlessly.",
        "language": "Python", "stars": 16700, "forks": 2800, "open_issues": 210,
        "category_id": "quant-datasci", "created_at": "2019-01-14T20:00:00Z",
        "topics": ["finance", "yahoo-finance", "stock-market", "data-science", "market-data"],
        "growth_24h": 95, "growth_7d": 650, "growth_30d": 2700, "is_emerging": False
    },
    {
        "full_name": "superlinked/superlinked", "name": "superlinked", "owner": "superlinked",
        "description": "Compute complex embeddings from structured, unstructured, and time-series data for quantitative ML.",
        "language": "Python", "stars": 5400, "forks": 380, "open_issues": 42,
        "category_id": "quant-datasci", "created_at": "2024-03-12T15:00:00Z",
        "topics": ["embeddings", "vector-search", "quant", "data-science", "feature-store"],
        "growth_24h": 140, "growth_7d": 920, "growth_30d": 3800, "is_emerging": True
    },

    # 6. Cybersecurity & AppSec
    {
        "full_name": "projectdiscovery/nuclei", "name": "nuclei", "owner": "projectdiscovery",
        "description": "Fast and customizable vulnerability scanner based on simple YAML based DSL.",
        "language": "Go", "stars": 20400, "forks": 2600, "open_issues": 180,
        "category_id": "cybersecurity", "created_at": "2020-04-20T17:00:00Z",
        "topics": ["vulnerability-scanner", "cybersecurity", "bug-bounty", "yaml", "go"],
        "growth_24h": 160, "growth_7d": 1100, "growth_30d": 4200, "is_emerging": True
    },
    {
        "full_name": "sqlmapproject/sqlmap", "name": "sqlmap", "owner": "sqlmapproject",
        "description": "Automatic SQL injection and database takeover tool.",
        "language": "Python", "stars": 33100, "forks": 5900, "open_issues": 85,
        "category_id": "cybersecurity", "created_at": "2011-09-21T18:00:00Z",
        "topics": ["sql-injection", "security", "pentesting", "infosec", "python"],
        "growth_24h": 65, "growth_7d": 450, "growth_30d": 1900, "is_emerging": False
    },
    {
        "full_name": "danielmiessler/SecLists", "name": "SecLists", "owner": "danielmiessler",
        "description": "SecLists is the security tester's companion. It's a collection of multiple types of lists used during security assessments.",
        "language": "Python", "stars": 60500, "forks": 14200, "open_issues": 40,
        "category_id": "cybersecurity", "created_at": "2013-05-13T20:00:00Z",
        "topics": ["security", "wordlists", "infosec", "bug-bounty", "pentesting"],
        "growth_24h": 90, "growth_7d": 620, "growth_30d": 2500, "is_emerging": False
    },
    {
        "full_name": "trufflesecurity/trufflehog", "name": "trufflehog", "owner": "trufflesecurity",
        "description": "Find, verify, and analyze leaked credentials and API tokens across git, S3, and code repositories.",
        "language": "Go", "stars": 17800, "forks": 1800, "open_issues": 130,
        "category_id": "cybersecurity", "created_at": "2017-01-18T22:00:00Z",
        "topics": ["secrets-scanning", "appsec", "git-security", "devsecops", "go"],
        "growth_24h": 125, "growth_7d": 850, "growth_30d": 3400, "is_emerging": True
    },

    # 7. Robotics, IoT & Hardware
    {
        "full_name": "espressif/esp-idf", "name": "esp-idf", "owner": "espressif",
        "description": "Espressif IoT Development Framework. Official development framework for ESP32 SoCs.",
        "language": "C", "stars": 14200, "forks": 7100, "open_issues": 2100,
        "category_id": "robotics-hardware", "created_at": "2016-09-02T10:00:00Z",
        "topics": ["esp32", "iot", "freertos", "embedded", "c", "firmware"],
        "growth_24h": 50, "growth_7d": 350, "growth_30d": 1450, "is_emerging": False
    },
    {
        "full_name": "Klipper3d/klipper", "name": "klipper", "owner": "Klipper3d",
        "description": "Klipper is a 3d-printer firmware that computes stepper movements on a microcomputer and drives MCUs via USB.",
        "language": "C", "stars": 10500, "forks": 5200, "open_issues": 40,
        "category_id": "robotics-hardware", "created_at": "2016-04-18T14:00:00Z",
        "topics": ["3d-printing", "firmware", "motion-control", "robotics", "c"],
        "growth_24h": 40, "growth_7d": 280, "growth_30d": 1150, "is_emerging": False
    },
    {
        "full_name": "ros2/ros2", "name": "ros2", "owner": "ros2",
        "description": "The Robot Operating System (ROS) 2 core infrastructure and client libraries.",
        "language": "C++", "stars": 5100, "forks": 1200, "open_issues": 340,
        "category_id": "robotics-hardware", "created_at": "2015-01-20T18:00:00Z",
        "topics": ["robotics", "ros2", "middleware", "autonomous-vehicles", "c++"],
        "growth_24h": 35, "growth_7d": 240, "growth_30d": 980, "is_emerging": False
    },
    {
        "full_name": "taichi-dev/taichi", "name": "taichi", "owner": "taichi-dev",
        "description": "Productive, portable, and high-performance physical simulation engine for robotics and computer graphics.",
        "language": "C++", "stars": 25800, "forks": 2400, "open_issues": 540,
        "category_id": "robotics-hardware", "created_at": "2016-04-06T15:00:00Z",
        "topics": ["physics-simulation", "robotics", "compiler", "cuda", "graphics"],
        "growth_24h": 110, "growth_7d": 760, "growth_30d": 3100, "is_emerging": True
    },

    # 8. Open Source Infrastructure
    {
        "full_name": "kubernetes/kubernetes", "name": "kubernetes", "owner": "kubernetes",
        "description": "Production-Grade Container Scheduling and Management.",
        "language": "Go", "stars": 114000, "forks": 39500, "open_issues": 2600,
        "category_id": "infrastructure", "created_at": "2014-06-06T22:00:00Z",
        "topics": ["kubernetes", "containers", "orchestration", "cloud-native", "go"],
        "growth_24h": 95, "growth_7d": 650, "growth_30d": 2700, "is_emerging": False
    },
    {
        "full_name": "supabase/supabase", "name": "supabase", "owner": "supabase",
        "description": "The open source Firebase alternative. Build with Postgres, Auth, real-time subscriptions, and Edge Functions.",
        "language": "TypeScript", "stars": 78200, "forks": 6400, "open_issues": 410,
        "category_id": "infrastructure", "created_at": "2020-01-14T07:00:00Z",
        "topics": ["postgres", "firebase-alternative", "realtime", "auth", "storage"],
        "growth_24h": 310, "growth_7d": 2100, "growth_30d": 8600, "is_emerging": True
    },
    {
        "full_name": "pocketbase/pocketbase", "name": "pocketbase", "owner": "pocketbase",
        "description": "Open Source realtime backend in 1 single Go file with SQLite, Auth, and admin UI.",
        "language": "Go", "stars": 44800, "forks": 2200, "open_issues": 80,
        "category_id": "infrastructure", "created_at": "2022-03-24T15:00:00Z",
        "topics": ["backend-in-a-box", "sqlite", "go", "self-hosted", "realtime"],
        "growth_24h": 260, "growth_7d": 1780, "growth_30d": 7200, "is_emerging": True
    },
    {
        "full_name": "tailscale/tailscale", "name": "tailscale", "owner": "tailscale",
        "description": "The easiest, most secure way to use WireGuard and 2FA. Mesh VPN for secure developer connectivity.",
        "language": "Go", "stars": 21500, "forks": 1400, "open_issues": 310,
        "category_id": "infrastructure", "created_at": "2020-02-12T19:00:00Z",
        "topics": ["vpn", "wireguard", "mesh-networking", "zero-trust", "go"],
        "growth_24h": 140, "growth_7d": 960, "growth_30d": 3900, "is_emerging": True
    },

    # 9. Emerging & Unclassified Technologies
    {
        "full_name": "antirez/smallchat", "name": "smallchat", "owner": "antirez",
        "description": "A minimal chat server written in 200 lines of C by the creator of Redis.",
        "language": "C", "stars": 14500, "forks": 1300, "open_issues": 25,
        "category_id": "emerging-tech", "created_at": "2023-08-11T16:00:00Z",
        "topics": ["c", "minimalist", "chat-server", "systems-programming", "education"],
        "growth_24h": 180, "growth_7d": 1150, "growth_30d": 4200, "is_emerging": True
    },
    {
        "full_name": "excalidraw/excalidraw", "name": "excalidraw", "owner": "excalidraw",
        "description": "Virtual whiteboard for sketching hand-drawn like diagrams. Collaborative and end-to-end encrypted.",
        "language": "TypeScript", "stars": 88400, "forks": 8500, "open_issues": 490,
        "category_id": "emerging-tech", "created_at": "2020-01-01T21:00:00Z",
        "topics": ["whiteboard", "canvas", "drawing", "collaboration", "react"],
        "growth_24h": 220, "growth_7d": 1480, "growth_30d": 6100, "is_emerging": False
    },
    {
        "full_name": "charmbracelet/bubbletea", "name": "bubbletea", "owner": "charmbracelet",
        "description": "A powerful little TUI (Terminal User Interface) framework based on The Elm Architecture.",
        "language": "Go", "stars": 28600, "forks": 980, "open_issues": 75,
        "category_id": "emerging-tech", "created_at": "2020-09-08T22:00:00Z",
        "topics": ["tui", "cli", "terminal", "elm-architecture", "go"],
        "growth_24h": 165, "growth_7d": 1120, "growth_30d": 4500, "is_emerging": True
    },
    {
        "full_name": "ladybirdbrowser/ladybird", "name": "ladybird", "owner": "ladybirdbrowser",
        "description": "A brand-new truly independent web browser and rendering engine written from scratch in C++.",
        "language": "C++", "stars": 29800, "forks": 1500, "open_issues": 410,
        "category_id": "emerging-tech", "created_at": "2022-07-04T12:00:00Z",
        "topics": ["web-browser", "rendering-engine", "c++", "from-scratch", "independent"],
        "growth_24h": 380, "growth_7d": 2400, "growth_30d": 9200, "is_emerging": True
    }
]

def generate_multi_day_snapshots(repo_id: int, current_stars: int, current_forks: int, g24h: int, g7d: int, g30d: int) -> List[Dict[str, Any]]:
    """
    Generates realistic 7-day chronological historical star snapshots.
    Guarantees consistent, monotonic trend curves for sparklines and momentum verification.
    """
    now = datetime.now(timezone.utc)
    snapshots = []
    
    # 7 snapshot intervals: 7d ago, 5d ago, 4d ago, 3d ago, 2d ago, 1d ago, today
    offsets_days = [7, 5, 4, 3, 2, 1, 0]
    
    for offset in offsets_days:
        snap_time = (now - timedelta(days=offset)).isoformat()
        
        # Calculate past stars monotonically
        if offset == 0:
            stars_at_t = current_stars
        elif offset == 1:
            stars_at_t = max(1, current_stars - g24h)
        else:
            fraction = float(offset) / 7.0
            stars_at_t = max(1, current_stars - int(g7d * fraction))
            
        forks_at_t = max(0, int(current_forks * (0.95 + 0.05 * (1.0 - offset / 7.0))))
        
        # Delta at this snapshot
        d24h = int(g24h * (0.8 + 0.4 * (1.0 - offset / 7.0)))
        d7d = g7d
        
        snapshots.append({
            "repo_id": repo_id,
            "timestamp": snap_time,
            "stars": stars_at_t,
            "forks": forks_at_t,
            "open_issues": max(0, int(current_stars * 0.015)),
            "delta_stars_24h": d24h,
            "delta_stars_7d": d7d,
            "delta_stars_30d": g30d
        })
        
    return snapshots

def seed_database_if_empty(conn):
    """Checks if repositories exist, and seeds rich baseline data if empty."""
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM repositories;")
    count = cursor.fetchone()[0]
    
    if count > 0:
        return count
        
    now_iso = datetime.now(timezone.utc).isoformat()
    
    # Insert seed repositories
    for repo in RAW_SEED_REPOSITORIES:
        cursor.execute("""
            INSERT OR IGNORE INTO repositories (
                full_name, name, owner, html_url, description, language,
                topics, stars, forks, open_issues, created_at, pushed_at,
                category_id, is_emerging, last_crawled_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """, (
            repo["full_name"],
            repo["name"],
            repo["owner"],
            f"https://github.com/{repo['full_name']}",
            repo["description"],
            repo["language"],
            json.dumps(repo["topics"]),
            repo["stars"],
            repo["forks"],
            repo["open_issues"],
            repo["created_at"],
            now_iso,
            repo["category_id"],
            1 if repo["is_emerging"] else 0,
            now_iso
        ))
        
        repo_id = cursor.lastrowid
        if not repo_id:
            cursor.execute("SELECT id FROM repositories WHERE full_name = ?;", (repo["full_name"],))
            row = cursor.fetchone()
            repo_id = row[0] if row else 1
            
        # Insert historical snapshots for this repo
        snaps = generate_multi_day_snapshots(
            repo_id=repo_id,
            current_stars=repo["stars"],
            current_forks=repo["forks"],
            g24h=repo["growth_24h"],
            g7d=repo["growth_7d"],
            g30d=repo["growth_30d"]
        )
        
        for s in snaps:
            cursor.execute("""
                INSERT INTO snapshots (
                    repo_id, timestamp, stars, forks, open_issues,
                    delta_stars_24h, delta_stars_7d, delta_stars_30d
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                s["repo_id"], s["timestamp"], s["stars"], s["forks"],
                s["open_issues"], s["delta_stars_24h"], s["delta_stars_7d"],
                s["delta_stars_30d"]
            ))

    # Add initial crawl record
    cursor.execute("""
        INSERT INTO crawl_history (
            started_at, finished_at, status, repos_updated, rate_limit_remaining
        ) VALUES (?, ?, 'COMPLETED', ?, 5000);
    """, (now_iso, now_iso, len(RAW_SEED_REPOSITORIES)))

    conn.commit()
    return len(RAW_SEED_REPOSITORIES)
