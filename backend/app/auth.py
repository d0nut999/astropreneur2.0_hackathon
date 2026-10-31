"""Authentication and authorization."""
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select
from .models import User, UserRole
from .db import get_session
from .config import settings


ph = PasswordHasher()


def hash_password(password: str) -> str:
    """Hash a password."""
    return ph.hash(password)


def verify_password(hashed: str, password: str) -> bool:
    """Verify password against hash."""
    try:
        ph.verify(hashed, password)
        return True
    except VerifyMismatchError:
        return False


def require_role(*allowed_roles: UserRole):
    """Dependency to check user role. Expects user_id in session/context."""
    def check_role(db: Session = Depends(get_session)) -> User:
        # Stub: In real app, extract user_id from session cookie
        # For now, return a mock user
        user = db.exec(select(User)).first()
        if not user or user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions"
            )
        return user

    return check_role
