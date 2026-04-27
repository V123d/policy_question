from datetime import datetime
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1)


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: "UserResponse"


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    id: UUID
    username: str
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    password: str = Field(..., min_length=6)
    role: str = Field(default="user", pattern="^(admin|user)$")


LoginResponse.model_rebuild()
