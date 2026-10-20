from fastapi import Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.core.security import decode_access_token
from backend.app.core.errors import AuthenticationError
from backend.app.database.session import get_db
from backend.app.database.models import User
from backend.app.auth.service import AuthService

security_scheme = HTTPBearer(auto_error=False)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    if not credentials or not credentials.credentials:
        raise AuthenticationError("Missing or invalid Authorization header")

    token_data = decode_access_token(credentials.credentials)
    if not token_data or "sub" not in token_data:
        raise AuthenticationError("Invalid or expired session token")

    # Strictly enforce token type: refresh tokens must not be accepted as access tokens
    if token_data.get("token_type") != "access":
        raise AuthenticationError("Invalid token type. Access token required.")

    user_id = token_data["sub"]
    token_version = token_data.get("token_version", 1)

    try:
        user = await AuthService.get_by_id(db, user_id)
    except Exception:
        raise AuthenticationError("User not found or session revoked")

    # Check for session revocation
    if user.token_version != token_version:
        raise AuthenticationError("Session has been revoked. Please log in again.")

    return user

async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    if not current_user.is_active:
        raise AuthenticationError("User account is inactive")
    return current_user
