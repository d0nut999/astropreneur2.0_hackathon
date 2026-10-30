"""User API routes."""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from database import get_db
from controllers.user_controller import UserController
from schemas.user import UserCreate, UserResponse, UserUpdate

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(user: UserCreate, db: Session = Depends(get_db)):
    """Create a new user."""
    return UserController.create_user(db, user)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get user by ID."""
    return UserController.get_user(db, user_id)


@router.get("/", response_model=list[UserResponse])
async def get_all_users(skip: int = 0, limit: int = 10, db: Session = Depends(get_db)):
    """Get all users."""
    return UserController.get_all_users(db, skip, limit)


@router.put("/{user_id}", response_model=UserResponse)
async def update_user(user_id: int, user_update: UserUpdate, db: Session = Depends(get_db)):
    """Update user."""
    return UserController.update_user(db, user_id, user_update)


@router.delete("/{user_id}")
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    """Delete user."""
    return UserController.delete_user(db, user_id)
