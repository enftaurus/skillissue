from typing import Optional
from fastapi import APIRouter, Depends, Request, Response, status, Cookie
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.database.session import get_db
from backend.app.database.models import User
from backend.app.auth.schemas import (
    UserRegister, UserLogin, Token, UserResponse, UserProfileResponse, UserProfileUpdate,
    RefreshTokenRequest, LogoutResponse
)
from backend.app.auth.service import AuthService
from backend.app.auth.dependencies import get_current_active_user
from backend.app.core.rate_limit import rate_limit
from backend.app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

REFRESH_COOKIE_NAME = "skillissue_refresh_token"

def set_refresh_cookie(response: Response, refresh_token: str):
    response.set_cookie(
        key=REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=(settings.ENVIRONMENT == "production"),
        samesite="strict",
        max_age=settings.REFRESH_TOKEN_EXPIRE_DAYS * 86400,
        path="/api/v1/auth"
    )

def clear_refresh_cookie(response: Response):
    response.delete_cookie(
        key=REFRESH_COOKIE_NAME,
        path="/api/v1/auth",
        httponly=True,
        samesite="strict",
    )

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(rate_limit(max_requests=10, window_seconds=60))]
)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    user = await AuthService.register(db, data)
    return user

@router.post(
    "/login",
    response_model=Token,
    dependencies=[Depends(rate_limit(max_requests=15, window_seconds=60))]
)
async def login(
    data: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db)
):
    token = await AuthService.authenticate(db, data)
    if token.refresh_token:
        set_refresh_cookie(response, token.refresh_token)
    return token

@router.post(
    "/refresh",
    response_model=Token,
    dependencies=[Depends(rate_limit(max_requests=30, window_seconds=60))]
)
async def refresh_token(
    response: Response,
    body: Optional[RefreshTokenRequest] = None,
    cookie_token: Optional[str] = Cookie(None, alias=REFRESH_COOKIE_NAME),
    db: AsyncSession = Depends(get_db)
):
    # Support both cookie and JSON body
    candidate_token = (body.refresh_token if body and body.refresh_token else None) or cookie_token
    if not candidate_token:
        from backend.app.core.errors import AuthenticationError
        raise AuthenticationError("Refresh token missing from request body and cookie")

    token = await AuthService.refresh_session(db, candidate_token)
    if token.refresh_token:
        set_refresh_cookie(response, token.refresh_token)
    return token

@router.post("/logout", response_model=LogoutResponse)
async def logout(
    response: Response,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    await AuthService.logout(db, current_user.id)
    clear_refresh_cookie(response)
    return LogoutResponse(status="logged_out", message="Session and all active refresh tokens revoked")

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_active_user)):
    return current_user

@router.put("/profile", response_model=UserProfileResponse)
async def update_profile(
    data: UserProfileUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    updated = await AuthService.update_profile(db, current_user.id, data)
    return updated

@router.delete("/account", status_code=status.HTTP_200_OK)
async def delete_account(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    await AuthService.delete_account(db, current_user.id)
    return {"status": "deleted", "message": "Account and all associated records permanently deleted"}
