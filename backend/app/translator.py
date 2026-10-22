"""
Native Translation Engine for GitPulse Explorer.
Detects and translates Chinese, Japanese, and Korean (CJK) repository descriptions
into English using Google Translate gtx with persistent SQLite caching.
"""

import ssl
import json
import re
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from typing import Optional, Dict
from app.config import DB_PATH

# CJK detection regex (Chinese Hanzi, Japanese Hiragana/Katakana, Korean Hangul)
CJK_REGEX = re.compile(r'[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7af]')

# Memory cache for fast zero-cost repetitive queries
_MEM_CACHE: Dict[str, str] = {}

def contains_cjk(text: Optional[str]) -> bool:
    """Returns True if the text contains Chinese, Japanese, or Korean characters."""
    if not text:
        return False
    return bool(CJK_REGEX.search(text))

def get_cached_translation_sync(conn, source_text: str) -> Optional[str]:
    """Retrieve translation from memory cache or SQLite translations table."""
    if not source_text:
        return None
    if source_text in _MEM_CACHE:
        return _MEM_CACHE[source_text]
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT translated_text FROM translations WHERE source_text = ? LIMIT 1;", (source_text,))
        row = cursor.fetchone()
        if row:
            translated = row[0]
            _MEM_CACHE[source_text] = translated
            return translated
    except Exception:
        pass
    return None

def save_translation_sync(conn, source_text: str, translated_text: str):
    """Save translation to memory cache and SQLite."""
    if not source_text or not translated_text:
        return
    _MEM_CACHE[source_text] = translated_text
    try:
        cursor = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        cursor.execute("""
            INSERT OR REPLACE INTO translations (source_text, translated_text, source_lang, created_at)
            VALUES (?, ?, 'cjk', ?);
        """, (source_text, translated_text, now_iso))
        conn.commit()
    except Exception:
        pass

def translate_cjk_sync(text: Optional[str], conn=None) -> Optional[str]:
    """
    Translates CJK text into English. Returns translated English string or original text on failure.
    """
    if not text or not contains_cjk(text):
        return None

    # Check cache
    if conn:
        cached = get_cached_translation_sync(conn, text)
        if cached:
            return cached
    elif text in _MEM_CACHE:
        return _MEM_CACHE[text]

    try:
        # Create unverified SSL context to prevent Windows cert store ASN1 issues
        ctx = ssl._create_unverified_context()
        encoded = urllib.parse.quote(text)
        url = f"https://translate.googleapis.com/translate_a/single?client=gtx&sl=auto&tl=en&dt=t&q={encoded}"
        
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            }
        )
        with urllib.request.urlopen(req, context=ctx, timeout=6) as resp:
            raw = resp.read().decode("utf-8", errors="ignore")
            data = json.loads(raw)
            if data and isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                translated = "".join(part[0] for part in data[0] if part and len(part) > 0 and part[0])
                if translated:
                    if conn:
                        save_translation_sync(conn, text, translated)
                    else:
                        _MEM_CACHE[text] = translated
                    return translated
    except Exception as e:
        print(f"[Translator] Translation error: {e}")

    return None

def batch_translate_cjk_repositories():
    """
    Scans repositories with CJK descriptions that lack description_en,
    translates them into English in batches, and updates the database.
    """
    import sqlite3
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, description FROM repositories 
        WHERE description IS NOT NULL 
          AND description != '' 
          AND (description_en IS NULL OR description_en = '');
    """)
    rows = cursor.fetchall()
    
    updated_count = 0
    for repo_id, desc in rows:
        if contains_cjk(desc):
            en_desc = translate_cjk_sync(desc, conn=conn)
            if en_desc:
                cursor.execute("UPDATE repositories SET description_en = ? WHERE id = ?;", (en_desc, repo_id))
                updated_count += 1
                if updated_count % 25 == 0:
                    conn.commit()
                    print(f"[Translator] Translated {updated_count} CJK repositories...")

    conn.commit()
    conn.close()
    print(f"[Translator] Complete. Total repositories translated: {updated_count}")
    return updated_count

if __name__ == "__main__":
    batch_translate_cjk_repositories()
