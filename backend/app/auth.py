"""
Authentication & Cryptographic Security Utility.
Provides zero-dependency, NIST-standard password hashing, constant-time verification,
session bearer token management, and optional/required FastAPI dependency authentication.
"""

import hashlib
import secrets
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from fastapi import Header, HTTPException, Depends
from app.database import get_db_connection

# Hash iterations following NIST SP 800-63B recommendations
PBKDF2_ITERATIONS = 100_000

def hash_password(password: str) -> str:
    """Hash password using salt + PBKDF2 HMAC-SHA256."""
    salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        'sha256',
        password.encode('utf-8'),
        salt.encode('utf-8'),
        PBKDF2_ITERATIONS
    )
    return f"{salt}${dk.hex()}"

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against stored salt and PBKDF2 hash using constant-time comparison."""
    if not hashed or '$' not in hashed:
        return False
    try:
        salt, hex_hash = hashed.split('$', 1)
        test_dk = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode('utf-8'),
            salt.encode('utf-8'),
            PBKDF2_ITERATIONS
        )
        return secrets.compare_digest(test_dk.hex(), hex_hash)
    except Exception:
        return False

def generate_session_token() -> str:
    """Generate a high-entropy URL-safe session token."""
    return secrets.token_urlsafe(32)

def generate_reset_code() -> str:
    """Generate a clean 6-digit numeric reset code."""
    return f"{secrets.randbelow(900000) + 100000}"

async def get_current_user_optional(
    authorization: Optional[str] = Header(None),
    db = Depends(get_db_connection)
) -> Optional[Dict[str, Any]]:
    """
    FastAPI dependency for OPTIONAL user authentication.
    Returns user dict if valid Bearer token provided; None otherwise.
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None

    token = authorization[7:].strip()
    if not token:
        return None

    now_iso = datetime.now(timezone.utc).isoformat()
    cursor = await db.execute("""
        SELECT u.id, u.email, u.name, u.created_at, s.expires_at
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.token = ? AND s.expires_at > ?
        LIMIT 1;
    """, (token, now_iso))
    row = await cursor.fetchone()

    if not row:
        return None

    return {
        "id": row["id"],
        "email": row["email"],
        "name": row["name"],
        "created_at": row["created_at"]
    }

async def get_current_user_required(
    user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)
) -> Dict[str, Any]:
    """
    FastAPI dependency for REQUIRED user authentication (e.g. saving bookmarks).
    Raises HTTP 401 if not authenticated.
    """
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Authentication required. Please sign in to access or modify your personal watchlist."
        )
    return user
