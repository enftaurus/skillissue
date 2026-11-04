"""Authentication and authorization dependencies for explanation checks and telemetry."""

from typing import Optional, Tuple
from fastapi import Depends, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.core.security import decode_access_token
from backend.app.core.errors import AuthenticationError
from backend.app.database.session import get_db
from backend.app.database.models import User, CandidateAssessment
from backend.app.auth.service import AuthService

security_scheme = HTTPBearer(auto_error=False)


async def get_integrity_actor(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    x_assessment_token: Optional[str] = Header(None, alias="X-Assessment-Token"),
    db: AsyncSession = Depends(get_db),
) -> Tuple[Optional[User], Optional[CandidateAssessment]]:
    """Resolve requesting actor as either an authenticated User or a CandidateAssessment.

    Returns:
        (current_user, candidate_assessment)
    """
    token_str = None
    if credentials and credentials.credentials:
        token_str = credentials.credentials
    elif x_assessment_token:
        token_str = x_assessment_token

    if not token_str:
        return None, None

    # 1. Try decoding as User JWT
    try:
        token_data = decode_access_token(token_str)
        if token_data and "sub" in token_data:
            user = await AuthService.get_by_id(db, token_data["sub"])
            if user and user.is_active:
                return user, None
    except Exception:
        pass

    # 2. Try looking up CandidateAssessment by access_token
    query = select(CandidateAssessment).where(CandidateAssessment.access_token == token_str)
    res = await db.execute(query)
    ca = res.scalar_one_or_none()
    if ca:
        return None, ca

    return None, None
