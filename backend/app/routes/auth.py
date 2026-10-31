"""Authentication routes."""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlmodel import Session, select

from ..audit import log_audit
from ..auth import (
    COOKIE_NAME, check_not_locked, clear_failures, create_session, delete_session, find_session, record_failure,
    require_user, verify_password,
)
from ..config import settings
from ..db import get_session
from ..models import User
from ..schemas import LoginRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(req: LoginRequest, request: Request, response: Response, db: Session = Depends(get_session)):
    email = req.email.strip().lower()
    key = f"{email}|{request.client.host if request.client else '?'}"
    check_not_locked(key)

    user = db.exec(select(User).where(User.email == email)).first()
    # same error message whether the email exists or not (no account enumeration)
    if not user or not verify_password(user.password_hash, req.password):
        record_failure(key)
        log_audit(db, actor="anonymous", action="login_failed", entity="user", entity_id=user.id if user else 0)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")

    clear_failures(key)
    token, csrf = create_session(db, user)
    response.set_cookie(
        COOKIE_NAME, token, httponly=True, samesite="lax", secure=settings.cookie_secure,
        max_age=settings.session_hours * 3600, path="/",
    )
    log_audit(db, actor=f"user:{user.id}", action="login", entity="user", entity_id=user.id)
    return {"id": user.id, "email": user.email, "role": user.role, "csrf_token": csrf}


@router.post("/logout")
def logout(request: Request, response: Response, db: Session = Depends(get_session)):
    token = request.cookies.get(COOKIE_NAME)
    sess = find_session(db, token)
    if sess:
        log_audit(db, actor=f"user:{sess.user_id}", action="logout", entity="user", entity_id=sess.user_id)
    delete_session(db, token)
    response.delete_cookie(COOKIE_NAME, path="/")
    return {"message": "Logged out"}


@router.get("/me")
def get_me(request: Request, user: User = Depends(require_user), db: Session = Depends(get_session)):
    sess = find_session(db, request.cookies.get(COOKIE_NAME))
    return {"id": user.id, "email": user.email, "role": user.role, "csrf_token": sess.csrf_token}
