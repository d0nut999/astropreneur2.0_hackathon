"""Authentication: argon2 passwords, server-side sessions in an HttpOnly cookie, CSRF protection.

- Login sets cookie `hg_session` (HttpOnly -> JavaScript cannot read it, SameSite=Lax).
- Every request that CHANGES something must also send header `X-CSRF-Token`
  (returned at login and by /auth/me). A malicious site cannot read it, so it cannot forge requests.
- Too many failed logins for the same email/IP -> temporary lock (brute-force protection).
"""
import hashlib
import secrets
import time
from datetime import datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, VerifyMismatchError
from fastapi import Depends, HTTPException, Request, status
from sqlmodel import Session, select

from .config import settings
from .db import get_session
from .models import User, UserRole, UserSession

ph = PasswordHasher()
COOKIE_NAME = "hg_session"
CSRF_HEADER = "X-CSRF-Token"
SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

# brute-force protection (in memory; fine for one server)
MAX_FAILED = 5
LOCK_SECONDS = 300
_failed: dict[str, list[float]] = {}


def hash_password(password: str) -> str:
    return ph.hash(password)


def verify_password(hashed: str, password: str) -> bool:
    try:
        return ph.verify(hashed, password)
    except (VerifyMismatchError, VerificationError, Exception):
        return False


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ---------- brute force ----------
def check_not_locked(key: str):
    now = time.time()
    attempts = [t for t in _failed.get(key, []) if now - t < LOCK_SECONDS]
    _failed[key] = attempts
    if len(attempts) >= MAX_FAILED:
        wait = int(LOCK_SECONDS - (now - attempts[0]))
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS,
                            f"Too many failed attempts. Try again in {wait // 60 + 1} minute(s).")


def record_failure(key: str):
    _failed.setdefault(key, []).append(time.time())


def clear_failures(key: str):
    _failed.pop(key, None)


# ---------- sessions ----------
def create_session(db: Session, user: User) -> tuple[str, str]:
    """Return (raw_token for the cookie, csrf_token)."""
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(24)
    db.add(UserSession(token_hash=_hash(token), csrf_token=csrf, user_id=user.id,
                       expires_at=datetime.now() + timedelta(hours=settings.session_hours)))
    db.commit()
    return token, csrf


def find_session(db: Session, token: str | None) -> UserSession | None:
    if not token:
        return None
    s = db.exec(select(UserSession).where(UserSession.token_hash == _hash(token))).first()
    if not s or s.expires_at < datetime.now():
        return None
    return s


def delete_session(db: Session, token: str | None):
    s = db.exec(select(UserSession).where(UserSession.token_hash == _hash(token or ""))).first()
    if s:
        db.delete(s)
        db.commit()


# ---------- dependencies ----------
def require_user(request: Request, db: Session = Depends(get_session)) -> User:
    """Logged-in user required. For changing requests, the CSRF header must match the session."""
    sess = find_session(db, request.cookies.get(COOKIE_NAME))
    if not sess:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please log in.")
    if request.method not in SAFE_METHODS:
        sent = request.headers.get(CSRF_HEADER, "")
        if not secrets.compare_digest(sent, sess.csrf_token):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Missing or invalid CSRF token.")
    user = db.get(User, sess.user_id)
    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Please log in.")
    return user


def require_role(*allowed_roles: UserRole):
    """Logged-in user with one of the given roles."""
    def check_role(user: User = Depends(require_user)) -> User:
        if user.role not in allowed_roles:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Insufficient permissions")
        return user

    return check_role
