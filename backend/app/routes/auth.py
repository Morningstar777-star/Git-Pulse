import re
from datetime import datetime, timezone, timedelta
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, Depends, HTTPException, Header
from app.database import get_db_connection
from app.auth import (
    hash_password,
    verify_password,
    generate_session_token,
    generate_reset_code,
    get_current_user_optional,
    get_current_user_required
)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

class SignUpRequest(BaseModel):
    email: str
    password: str = Field(min_length=6)
    name: Optional[str] = None

class SignInRequest(BaseModel):
    email: str
    password: str

class ForgotPasswordRequest(BaseModel):
    email: str

class ResetPasswordRequest(BaseModel):
    email: str
    reset_code: str
    new_password: str = Field(min_length=6)

class AuthResponse(BaseModel):
    token: str
    user: dict

@router.post("/signup", response_model=AuthResponse)
async def sign_up(req: SignUpRequest, db=Depends(get_db_connection)):
    """Register a new user account."""
    clean_email = req.email.strip().lower()
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean_email):
        raise HTTPException(status_code=400, detail="Invalid email address format.")

    # Check for existing email
    cursor = await db.execute("SELECT id FROM users WHERE email = ? LIMIT 1;", (clean_email,))
    if await cursor.fetchone():
        raise HTTPException(status_code=400, detail="An account with this email already exists.")

    pwd_hash = hash_password(req.password)
    user_name = (req.name or clean_email.split('@')[0]).strip()
    now_iso = datetime.now(timezone.utc).isoformat()

    cursor = await db.execute("""
        INSERT INTO users (email, password_hash, name, created_at)
        VALUES (?, ?, ?, ?);
    """, (clean_email, pwd_hash, user_name, now_iso))
    await db.commit()
    user_id = cursor.lastrowid

    # Create 30-day session
    token = generate_session_token()
    expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    await db.execute("""
        INSERT INTO sessions (token, user_id, created_at, expires_at)
        VALUES (?, ?, ?, ?);
    """, (token, user_id, now_iso, expires_at))
    await db.commit()

    return AuthResponse(
        token=token,
        user={"id": user_id, "email": clean_email, "name": user_name, "created_at": now_iso}
    )

@router.post("/signin", response_model=AuthResponse)
async def sign_in(req: SignInRequest, db=Depends(get_db_connection)):
    """Authenticate with email and password."""
    clean_email = req.email.strip().lower()

    cursor = await db.execute("""
        SELECT id, email, password_hash, name, created_at
        FROM users
        WHERE email = ?
        LIMIT 1;
    """, (clean_email,))
    row = await cursor.fetchone()

    if not row or not verify_password(req.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    user_id = row["id"]
    token = generate_session_token()
    now_iso = datetime.now(timezone.utc).isoformat()
    expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()

    await db.execute("""
        INSERT INTO sessions (token, user_id, created_at, expires_at)
        VALUES (?, ?, ?, ?);
    """, (token, user_id, now_iso, expires_at))
    await db.commit()

    return AuthResponse(
        token=token,
        user={"id": user_id, "email": row["email"], "name": row["name"], "created_at": row["created_at"]}
    )

@router.get("/me")
async def get_me(user: dict = Depends(get_current_user_required)):
    """Retrieve currently authenticated user profile."""
    return {"user": user}

@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest, db=Depends(get_db_connection)):
    """
    Generate password reset verification code for user's email.
    Returns code directly in payload for instant live demonstration & tests.
    """
    clean_email = req.email.strip().lower()
    cursor = await db.execute("SELECT id, name FROM users WHERE email = ? LIMIT 1;", (clean_email,))
    row = await cursor.fetchone()

    if not row:
        # Prevent user enumeration by returning standard message, but note not found
        return {
            "status": "NOT_FOUND",
            "message": "If this email is registered, a password reset code has been generated."
        }

    reset_code = generate_reset_code()
    reset_token = generate_session_token()
    expires_at = (datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat()

    await db.execute("""
        UPDATE users
        SET reset_token = ?, reset_code = ?, reset_expires_at = ?
        WHERE id = ?;
    """, (reset_token, reset_code, expires_at, row["id"]))
    await db.commit()

    return {
        "status": "SUCCESS",
        "message": f"Reset code generated for {clean_email}. Valid for 15 minutes.",
        "reset_code": reset_code,
        "reset_token": reset_token
    }

@router.post("/reset-password", response_model=AuthResponse)
async def reset_password(req: ResetPasswordRequest, db=Depends(get_db_connection)):
    """Verify reset code and set new password."""
    clean_email = req.email.strip().lower()
    clean_code = req.reset_code.strip()
    now_iso = datetime.now(timezone.utc).isoformat()

    cursor = await db.execute("""
        SELECT id, email, name, reset_expires_at
        FROM users
        WHERE email = ? AND reset_code = ?
        LIMIT 1;
    """, (clean_email, clean_code))
    row = await cursor.fetchone()

    if not row:
        raise HTTPException(status_code=400, detail="Invalid verification code or email.")

    if row["reset_expires_at"] < now_iso:
        raise HTTPException(status_code=400, detail="Verification code has expired. Please request a new code.")

    user_id = row["id"]
    new_hash = hash_password(req.new_password)

    # Update password and clear reset code
    await db.execute("""
        UPDATE users
        SET password_hash = ?, reset_token = NULL, reset_code = NULL, reset_expires_at = NULL
        WHERE id = ?;
    """, (new_hash, user_id))

    # Invalidate all prior sessions
    await db.execute("DELETE FROM sessions WHERE user_id = ?;", (user_id,))

    # Create new active session
    token = generate_session_token()
    expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
    await db.execute("""
        INSERT INTO sessions (token, user_id, created_at, expires_at)
        VALUES (?, ?, ?, ?);
    """, (token, user_id, now_iso, expires_at))
    await db.commit()

    return AuthResponse(
        token=token,
        user={"id": user_id, "email": row["email"], "name": row["name"], "created_at": now_iso}
    )

@router.post("/signout")
async def sign_out(
    authorization: Optional[str] = Header(None),
    db=Depends(get_db_connection)
):
    """Sign out and invalidate current bearer session token."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization[7:].strip()
        await db.execute("DELETE FROM sessions WHERE token = ?;", (token,))
        await db.commit()
    return {"status": "SUCCESS", "message": "Signed out successfully."}
