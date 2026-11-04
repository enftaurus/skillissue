import pytest_asyncio
from typing import AsyncGenerator
import httpx
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.pool import NullPool
from backend.app.core.config import settings
from backend.app.database.session import Base, get_db
from backend.app.main import create_application

@pytest_asyncio.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    engine = create_async_engine(settings.DATABASE_URL, poolclass=NullPool, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
    await engine.dispose()

@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[httpx.AsyncClient, None]:
    app = create_application()
    app.dependency_overrides[get_db] = lambda: db_session

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

@pytest_asyncio.fixture
async def create_test_user(db_session: AsyncSession):
    import uuid
    from backend.app.core.security import hash_password
    from backend.app.database.models import User, UserProfile, ProviderConfig

    async def _create(
        email: str,
        password: str = "Password123!",
        role: str = "candidate",
        tenant_id: str = "tenant-prod-default",
        is_test: bool = False
    ) -> User:
        user = User(
            email=email.lower(),
            hashed_password=hash_password(password),
            role=role,
            tenant_id=tenant_id,
            is_test=is_test,
            is_active=True,
            onboarding_completed=True,
            token_version=1,
        )
        db_session.add(user)
        await db_session.flush()
        profile = UserProfile(user_id=user.id, target_role="Engineer")
        db_session.add(profile)
        config = ProviderConfig(user_id=user.id, provider_name="mock", is_valid=True)
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(user)
        return user
    return _create

@pytest_asyncio.fixture
async def create_test_tenant(db_session: AsyncSession):
    import uuid
    import re
    from backend.app.database.models import Tenant

    async def _create(name: str, slug: str = None, is_test: bool = False) -> Tenant:
        s = slug or f"{re.sub(r'[^a-z0-9]+', '-', name.lower()).strip('-')}-{uuid.uuid4().hex[:6]}"
        tenant = Tenant(name=name, slug=s, is_test=is_test)
        db_session.add(tenant)
        await db_session.commit()
        await db_session.refresh(tenant)
        return tenant
    return _create

