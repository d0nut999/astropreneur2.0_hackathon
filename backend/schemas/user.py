"""User schemas for API requests and responses."""
from pydantic import BaseModel, EmailStr
from datetime import datetime


class UserCreate(BaseModel):
    """Schema for creating a new user."""
    email: EmailStr
    username: str
    full_name: str | None = None
    password: str

    model_config = {"json_schema_extra": {
        "example": {
            "email": "user@example.com",
            "username": "john_doe",
            "full_name": "John Doe",
            "password": "securepassword123"
        }
    }}


class UserUpdate(BaseModel):
    """Schema for updating user."""
    full_name: str | None = None
    email: EmailStr | None = None

    model_config = {"json_schema_extra": {
        "example": {
            "full_name": "Jane Doe",
            "email": "jane@example.com"
        }
    }}


class UserResponse(BaseModel):
    """Schema for user response."""
    id: int
    email: str
    username: str
    full_name: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
