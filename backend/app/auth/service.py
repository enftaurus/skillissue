from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from backend.app.core.security import hash_password, verify_password, create_access_token
from backend.app.core.errors import AppException, AuthenticationError, EntityNotFoundError
from backend.app.database.models import User, UserProfile, ProviderConfig
from backend.app.auth.schemas import UserRegister, UserLogin, Token, UserProfileUpdate

class AuthService:
    @staticmethod
    async def register(db: AsyncSession, data: UserRegister) -> User:
        # Check if user already exists
        result = await db.execute(select(User).where(User.email == data.email.lower()))
        if result.scalar_one_or_none():
            raise AppException("An account with this email address already exists", code="EMAIL_ALREADY_EXISTS")

        # Create user
        user = User(
            email=data.email.lower(),
            hashed_password=hash_password(data.password),
            is_active=True,
        )
        db.add(user)
        await db.flush()

        # Create user profile
        profile = UserProfile(
            user_id=user.id,
            target_role=data.target_role or "Software Engineer",
            years_experience=data.years_experience or 0.0,
            daily_study_minutes=data.daily_study_minutes or 45,
        )
        db.add(profile)

        # Create initial default provider config (mock mode by default)
        config = ProviderConfig(
            user_id=user.id,
            provider_name="mock",
            preferred_model="mock-claude-3-5-sonnet",
            is_valid=True,
        )
        db.add(config)
        await db.commit()
        await db.refresh(user, ["profile", "provider_config"])
        return user

    @staticmethod
    async def authenticate(db: AsyncSession, data: UserLogin) -> Token:
        result = await db.execute(
            select(User)
            .options(selectinload(User.profile))
            .where(User.email == data.email.lower())
        )
        user = result.scalar_one_or_none()
        if not user or not verify_password(data.password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")
        if not user.is_active:
            raise AuthenticationError("Account has been deactivated")

        token = create_access_token(subject=user.id)
        return Token(
            access_token=token,
            user_id=user.id,
            email=user.email,
        )

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: str) -> User:
        result = await db.execute(
            select(User)
            .options(selectinload(User.profile), selectinload(User.provider_config))
            .where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        if not user:
            raise EntityNotFoundError("User", user_id)
        return user

    @staticmethod
    async def update_profile(db: AsyncSession, user_id: str, data: UserProfileUpdate) -> UserProfile:
        result = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        profile = result.scalar_one_or_none()
        if not profile:
            raise EntityNotFoundError("UserProfile", user_id)

        if data.target_role is not None:
            profile.target_role = data.target_role
        if data.years_experience is not None:
            profile.years_experience = data.years_experience
        if data.daily_study_minutes is not None:
            profile.daily_study_minutes = data.daily_study_minutes
        if data.bio is not None:
            profile.bio = data.bio

        await db.commit()
        await db.refresh(profile)
        return profile

    @staticmethod
    async def delete_account(db: AsyncSession, user_id: str) -> bool:
        user = await AuthService.get_by_id(db, user_id)
        await db.delete(user)
        await db.commit()
        return True
