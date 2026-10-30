"""User controller for business logic."""
from sqlalchemy.orm import Session
from repositories.user_repository import UserRepository
from schemas.user import UserCreate, UserResponse, UserUpdate
from fastapi import HTTPException, status


class UserController:
    """Controller for user operations."""

    @staticmethod
    def create_user(db: Session, user: UserCreate) -> UserResponse:
        """Create a new user."""
        # Check if user already exists
        existing_email = UserRepository.get_user_by_email(db, user.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        existing_username = UserRepository.get_user_by_username(db, user.username)
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken",
            )

        # Simple hash (use bcrypt in production)
        hashed_password = UserController._hash_password(user.password)

        db_user = UserRepository.create_user(db, user, hashed_password)
        return UserResponse.model_validate(db_user)

    @staticmethod
    def get_user(db: Session, user_id: int) -> UserResponse:
        """Get user by ID."""
        db_user = UserRepository.get_user_by_id(db, user_id)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return UserResponse.model_validate(db_user)

    @staticmethod
    def get_all_users(db: Session, skip: int = 0, limit: int = 10) -> list[UserResponse]:
        """Get all users."""
        users = UserRepository.get_all_users(db, skip, limit)
        return [UserResponse.model_validate(user) for user in users]

    @staticmethod
    def update_user(db: Session, user_id: int, user_update: UserUpdate) -> UserResponse:
        """Update user."""
        db_user = UserRepository.update_user(db, user_id, user_update)
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return UserResponse.model_validate(db_user)

    @staticmethod
    def delete_user(db: Session, user_id: int) -> dict:
        """Delete user."""
        success = UserRepository.delete_user(db, user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return {"message": "User deleted successfully"}

    @staticmethod
    def _hash_password(password: str) -> str:
        """Hash password (use bcrypt in production)."""
        # TODO: Replace with bcrypt
        import hashlib
        return hashlib.sha256(password.encode()).hexdigest()
