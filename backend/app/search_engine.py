"""
Smart Natural Language Search & Semantic Intent Intelligence Engine.
Understands conversational prompts, domain keywords, concept intersections,
and multi-tag relationships to rank repositories with extreme precision.
"""

import re
import math
from typing import Dict, Any, List, Set, Tuple

# Common conversational English stopwords & filler phrases
STOP_WORDS: Set[str] = {
    "i", "want", "to", "build", "a", "an", "the", "and", "in", "it", "give", "better",
    "look", "using", "use", "make", "create", "need", "looking", "for", "find", "is",
    "are", "with", "that", "how", "what", "can", "help", "me", "some", "good", "best",
    "of", "from", "on", "at", "by", "as", "about", "into", "through", "there", "then",
    "or", "so", "just", "my", "our", "their", "all", "which", "would", "like", "also",
    "have", "has", "had", "will", "do", "does", "did", "tool", "tools", "library", "libraries",
    "project", "projects", "repo", "repos", "repository", "repositories", "code", "app", "application"
}

# Typo normalization map
TYPO_CORRECTIONS: Dict[str, str] = {
    "vidualization": "visualization",
    "visualisation": "visualization",
    "vidual": "visual",
    "speach": "speech",
    "artifical": "artificial",
    "modles": "models",
    "algoritm": "algorithm",
    "translat": "translate",
    "interfac": "interface",
    "computr": "computer",
    "languag": "language",
    "recogntion": "recognition",
    "synthesiz": "synthesis",
    "clonning": "cloning",
}

# Domain Concept Ontologies
DOMAIN_CONCEPTS: Dict[str, Set[str]] = {
    "3d": {
        "3d", "threejs", "three.js", "three", "webgl", "model", "models", "rendering",
        "visualization", "mesh", "gltf", "obj", "blender", "spline", "shader", "graphics",
        "babylon", "babylonjs", "canvas", "opengl", "computer-graphics", "3d-model", "vulkan",
        "raymarching", "render", "3d-printing", "cad", "spatial"
    },
    "web": {
        "website", "web", "frontend", "ui", "components", "react", "vue", "html", "css",
        "tailwind", "nextjs", "landing", "dashboard", "dom", "browser", "javascript",
        "typescript", "web-framework", "design-system", "astro", "svelte"
    },
    "speech": {
        "speech", "tts", "text-to-speech", "speech-to-text", "stt", "voice", "whisper",
        "asr", "voice-cloning", "speech-synthesis", "audio", "sound", "music",
        "transcription", "synthesizer", "vits", "valle", "chatterbox", "fish-speech",
        "wav2lip", "deepspeech", "sovits", "gpt-sovits", "voice-assistant", "speech-recognition"
    },
    "ai_agents": {
        "llm", "agent", "agents", "gpt", "gpt-4", "claude", "deepseek", "ollama", "rag",
        "langchain", "crewai", "chatbot", "mcp", "transformer", "nlp", "ai",
        "artificial-intelligence", "autonomous-agents", "prompt", "reasoning", "agentic"
    },
    "vision": {
        "computer-vision", "vision", "image", "diffusion", "stable-diffusion", "comfyui",
        "opencv", "yolo", "flux", "photo", "segmentation", "detection", "ocr", "photocraft",
        "vectorcraft", "generative-art"
    },
    "audio": {
        "audio", "sound", "music", "dsp", "voice", "speech", "synthesizer", "karaoke",
        "equalizer", "audio-processing"
    },
    "security": {
        "security", "cybersecurity", "pentest", "exploit", "vulnerability", "adblock",
        "privacy", "malware", "firewall", "debloat", "encryption", "reverse-engineering"
    },
    "finance": {
        "trading", "crypto", "finance", "quantitative-finance", "backtest", "stocks",
        "bitcoin", "solana", "algorithmic-trading", "investing"
    },
    "infra_dev": {
        "cli", "terminal", "shell", "bash", "zsh", "docker", "kubernetes", "devops",
        "tui", "system-design", "linux", "workflow", "developer-tools"
    }
}

def parse_search_intent(query_str: str) -> Dict[str, Any]:
    """
    Parses a conversational natural language search query into semantic concepts,
    keywords, and multi-concept intent.
    """
    raw_clean = query_str.strip()
    # Strip URL prefixes if user pasted a GitHub URL
    raw_clean = re.sub(r"^https?://github\.com/", "", raw_clean, flags=re.IGNORECASE)
    raw_clean = re.sub(r"^github\.com/", "", raw_clean, flags=re.IGNORECASE).strip("/")

    # Tokenize into words
    words = re.findall(r'[a-zA-Z0-9_\-\.]+', raw_clean.lower())
    
    # Correct typos and normalize
    normalized_words = [TYPO_CORRECTIONS.get(w, w) for w in words]

    # Meaningful domain keywords (excluding stopwords)
    meaningful_keywords = [w for w in normalized_words if w not in STOP_WORDS and len(w) > 1]
    if not meaningful_keywords:
        # Fallback to whatever words were passed
        meaningful_keywords = normalized_words

    # Detect matching concepts
    matched_concept_names: Set[str] = set()
    expanded_terms: Set[str] = set(meaningful_keywords)

    for word in meaningful_keywords:
        for concept_name, term_set in DOMAIN_CONCEPTS.items():
            if word in term_set:
                matched_concept_names.add(concept_name)
                # Add top terms from this concept
                expanded_terms.update(list(term_set)[:10])

    is_multi_concept = len(matched_concept_names) >= 2

    # Build targeted compact query for GitHub API fallback
    top_terms = meaningful_keywords[:3]
    github_query = " ".join(top_terms)

    return {
        "raw_query": query_str,
        "clean_query": raw_clean,
        "meaningful_keywords": meaningful_keywords,
        "matched_concepts": list(matched_concept_names),
        "is_multi_concept": is_multi_concept,
        "expanded_terms": list(expanded_terms),
        "github_query": github_query
    }

def score_repository_relevance(repo: Dict[str, Any], intent: Dict[str, Any]) -> float:
    """
    Calculates semantic relevance score (0 - 1000+) for a repository
    given the parsed search intent.
    """
    clean_query = intent["clean_query"].lower()
    keywords = intent["meaningful_keywords"]
    expanded_terms = set(intent["expanded_terms"])
    matched_concepts = intent["matched_concepts"]

    name_lower = (repo.get("name") or "").lower()
    full_name_lower = (repo.get("full_name") or "").lower()
    desc_lower = (repo.get("description") or "").lower()
    desc_en_lower = (repo.get("description_en") or "").lower()
    topics_list = [t.lower() for t in (repo.get("topics") or [])]
    topics_text = " ".join(topics_list)

    score = 0.0

    # 1. Exact match on repo name or full_name
    if clean_query == name_lower:
        score += 300.0
    elif clean_query == full_name_lower:
        score += 350.0
    elif clean_query in full_name_lower:
        score += 180.0
    elif clean_query in name_lower:
        score += 150.0

    # 2. Meaningful keywords matching
    matched_keyword_count = 0
    for kw in keywords:
        kw_matched = False
        if kw == name_lower:
            score += 120.0
            kw_matched = True
        elif kw in name_lower:
            score += 70.0
            kw_matched = True

        if kw in full_name_lower:
            score += 50.0
            kw_matched = True

        if kw in topics_list:
            score += 80.0
            kw_matched = True
        elif any(kw in t for t in topics_list):
            score += 50.0
            kw_matched = True

        # Check in English description or translated description
        if desc_en_lower and kw in desc_en_lower:
            score += 45.0
            kw_matched = True
        elif kw in desc_lower:
            score += 35.0
            kw_matched = True

        if kw_matched:
            matched_keyword_count += 1

    # Ratio of matched keywords
    if keywords:
        keyword_coverage = matched_keyword_count / len(keywords)
        score += keyword_coverage * 100.0

    # 3. Concept expansion matching
    for term in expanded_terms:
        if term in topics_list:
            score += 25.0
        elif term in name_lower:
            score += 20.0
        elif desc_en_lower and term in desc_en_lower:
            score += 15.0
        elif term in desc_lower:
            score += 10.0

    # 4. Multi-concept intersection bonus (e.g. user asked for "website" + "3d models")
    if intent["is_multi_concept"]:
        concepts_hit = set()
        for c_name in matched_concepts:
            c_terms = DOMAIN_CONCEPTS.get(c_name, set())
            if any(t in name_lower or t in topics_text or t in desc_lower or t in desc_en_lower for t in c_terms):
                concepts_hit.add(c_name)
        
        # If repo satisfies 2 or more of the user's distinct conceptual desires
        if len(concepts_hit) >= 2:
            score = (score + 100.0) * 2.2
        elif len(concepts_hit) == 1:
            score = score * 1.2

    # 5. Quality & Momentum blending (surface top-tier & breakout relevant projects)
    if score > 0:
        stars = max(1, repo.get("stars", 0))
        momentum = float(repo.get("momentum_score", 0.0) or 0.0)
        stars_boost = min(25.0, math.log10(stars) * 4.0)
        momentum_boost = momentum * 0.15
        score += stars_boost + momentum_boost

    return score
