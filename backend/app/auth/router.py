from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID

from app.database import get_db
from app.auth.service import hash_password, verify_password, create_access_token, create_refresh_token, verify_refresh_token
from app.auth.schemas import LoginRequest, LoginResponse, RefreshRequest, RefreshResponse, RegisterRequest, UserResponse
from app.dependencies import get_current_user
from app.policies.models import User, ChatLog
from app.config import get_settings

router = APIRouter(prefix="/api/auth", tags=["认证"])
settings = get_settings()


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == request.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )

    token_data = {"sub": str(user.id), "role": user.role, "username": user.username}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.access_token_expire_minutes * 60,
        user=UserResponse.model_validate(user),
    )


@router.post("/register", response_model=UserResponse)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == request.username))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名已存在",
        )

    user = User(
        username=request.username,
        password_hash=hash_password(request.password),
        role=request.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_token(request: RefreshRequest, db: AsyncSession = Depends(get_db)):
    payload = verify_refresh_token(request.refresh_token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh Token已过期或无效",
        )

    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
        )

    token_data = {"sub": str(user.id), "role": user.role, "username": user.username}
    access_token = create_access_token(token_data)

    return RefreshResponse(
        access_token=access_token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return UserResponse.model_validate(current_user)
