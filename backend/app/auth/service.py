from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from backend.app.core.security import (
    hash_password, verify_password, dummy_verify_password,
    create_access_token, create_refresh_token, decode_access_token
)
from backend.app.core.errors import AppException, AuthenticationError, EntityNotFoundError
import os
import re
import uuid
from backend.app.core.config import settings
from backend.app.database.models import User, UserProfile, ProviderConfig, Tenant
from backend.app.auth.schemas import UserRegister, RecruiterRegister, UserLogin, Token, UserProfileUpdate

class AuthService:
    @staticmethod
    async def register(db: AsyncSession, data: UserRegister) -> User:
        # Check if user already exists
        result = await db.execute(select(User).where(User.email == data.email.lower()))
        if result.scalar_one_or_none():
            raise AppException("An account with this email address already exists", code="EMAIL_ALREADY_EXISTS")

        # Public register always creates role=candidate
        # is_test is settable only by admin or env flag ALLOW_TEST_USERS=true in non-production
        allow_test = (os.environ.get("ALLOW_TEST_USERS", "").lower() == "true") and (settings.ENVIRONMENT != "production")
        is_test = bool(allow_test)
        tenant_id = "tenant-test-sandbox" if is_test else "tenant-prod-default"

        user = User(
            email=data.email.lower(),
            hashed_password=hash_password(data.password),
            role="candidate",
            tenant_id=tenant_id,
            is_test=is_test,
            is_active=True,
            onboarding_completed=False,
            token_version=1,
        )
        db.add(user)
        await db.flush()

        # Create user profile with sensible defaults
        profile = UserProfile(
            user_id=user.id,
            target_role="Software Engineer",
            years_experience=0.0,
            daily_study_minutes=45,
        )
        db.add(profile)

        # Create initial unconfigured Bedrock provider config (requires BYOC setup)
        from backend.app.providers.models_catalog import DEFAULT_MODEL_ID
        config = ProviderConfig(
            user_id=user.id,
            provider_name="bedrock",
            aws_region="us-east-1",
            preferred_model=DEFAULT_MODEL_ID,
            default_model=DEFAULT_MODEL_ID,
            is_valid=False,
        )
        db.add(config)
        await db.commit()
        await db.refresh(user, ["profile", "provider_config"])
        return user

    @staticmethod
    async def register_recruiter(db: AsyncSession, data: RecruiterRegister) -> User:
        # Check if user already exists
        result = await db.execute(select(User).where(User.email == data.email.lower()))
        if result.scalar_one_or_none():
            raise AppException("An account with this email address already exists", code="EMAIL_ALREADY_EXISTS")

        # Generate unique tenant slug from organisation name
        base_slug = re.sub(r'[^a-z0-9]+', '-', data.organisation_name.lower()).strip('-') or 'org'
        existing_tenant = await db.execute(select(Tenant).where(Tenant.slug == base_slug))
        slug = f"{base_slug}-{uuid.uuid4().hex[:6]}" if existing_tenant.scalar_one_or_none() else base_slug

        tenant = Tenant(
            name=data.organisation_name.strip(),
            slug=slug,
            is_test=False,
        )
        db.add(tenant)
        await db.flush()

        user = User(
            email=data.email.lower(),
            hashed_password=hash_password(data.password),
            role="recruiter",
            tenant_id=tenant.id,
            is_test=False,
            is_active=True,
            onboarding_completed=True,
            token_version=1,
        )
        db.add(user)
        await db.flush()

        profile = UserProfile(
            user_id=user.id,
            target_role="Recruiter / Talent Lead",
            years_experience=0.0,
            daily_study_minutes=0,
        )
        db.add(profile)

        from backend.app.providers.models_catalog import DEFAULT_MODEL_ID
        config = ProviderConfig(
            user_id=user.id,
            provider_name="mock",
            aws_region="us-east-1",
            preferred_model=DEFAULT_MODEL_ID,
            default_model=DEFAULT_MODEL_ID,
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
            .options(selectinload(User.profile), selectinload(User.provider_config))
            .where(User.email == data.email.lower())
        )
        user = result.scalar_one_or_none()
        
        # Constant-time mitigation against email enumeration attacks
        if not user:
            dummy_verify_password(data.password)
            raise AuthenticationError("Invalid email or password")
            
        if not verify_password(data.password, user.hashed_password):
            raise AuthenticationError("Invalid email or password")

        if not user.is_active:
            raise AuthenticationError("Account has been deactivated")

        access_token = create_access_token(subject=user.id, token_version=user.token_version)
        refresh_token = create_refresh_token(subject=user.id, token_version=user.token_version)

        is_onboarded = bool(user.onboarding_completed and user.provider_config and user.provider_config.is_valid)

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user.id,
            email=user.email,
            role=user.role,
            tenant_id=user.tenant_id,
            is_test=user.is_test,
            onboarding_completed=is_onboarded,
        )

    @staticmethod
    async def refresh_session(db: AsyncSession, refresh_token: str) -> Token:
        token_data = decode_access_token(refresh_token)
        if not token_data or "sub" not in token_data:
            raise AuthenticationError("Invalid or expired refresh token")

        if token_data.get("token_type") != "refresh":
            raise AuthenticationError("Invalid token type for refresh")

        user_id = token_data["sub"]
        token_version = token_data.get("token_version", 1)

        user = await AuthService.get_by_id(db, user_id)
        if user.token_version != token_version:
            raise AuthenticationError("Session has been revoked. Please log in again.")

        if not user.is_active:
            raise AuthenticationError("Account has been deactivated")

        new_access_token = create_access_token(subject=user.id, token_version=user.token_version)
        new_refresh_token = create_refresh_token(subject=user.id, token_version=user.token_version)

        is_onboarded = bool(user.onboarding_completed and user.provider_config and user.provider_config.is_valid)

        return Token(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            user_id=user.id,
            email=user.email,
            role=user.role,
            tenant_id=user.tenant_id,
            is_test=user.is_test,
            onboarding_completed=is_onboarded,
        )

    @staticmethod
    async def logout(db: AsyncSession, user_id: str) -> bool:
        """Revoke all issued sessions by incrementing user token_version."""
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            user.token_version += 1
            await db.commit()
        return True

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
