"""Authentication routes."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from ..db import get_session
from ..models import User, UserRole
from ..schemas import LoginRequest, UserResponse
from ..auth import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
async def login(req: LoginRequest, db: Session = Depends(get_session)):
    """Login and return user (stub: no session cookie yet)."""
    user = db.exec(select(User).where(User.email == req.email)).first()
    if not user or not verify_password(user.password_hash, req.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    return UserResponse(id=user.id, email=user.email, role=user.role)


@router.post("/logout")
async def logout():
    """Logout (stub)."""
    return {"message": "Logged out"}


@router.get("/me")
async def get_me(db: Session = Depends(get_session)):
    """Get current user (stub: return first user for now)."""
    user = db.exec(select(User)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not logged in"
        )
    return UserResponse(id=user.id, email=user.email, role=user.role)
