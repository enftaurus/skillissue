import asyncio
from sqlalchemy import select, update, func
from backend.app.database.session import AsyncSessionLocal
from backend.app.database.models import User, Tenant, UserProfile
from backend.app.core.security import hash_password

async def partition_database():
    print("=== Partitioning Production Database ===")
    async with AsyncSessionLocal() as session:
        # 1. Ensure production tenant exists and is marked is_test=False
        prod_tenant = (await session.execute(
            select(Tenant).where(Tenant.id == "tenant-prod-default")
        )).scalar_one_or_none()
        
        if not prod_tenant:
            prod_tenant = Tenant(
                id="tenant-prod-default",
                name="Production Candidates",
                slug="default",
                is_test=False
            )
            session.add(prod_tenant)
        else:
            prod_tenant.is_test = False
            prod_tenant.name = "Production Candidates"
            prod_tenant.slug = "default"

        # 2. Ensure test sandbox tenant exists and is marked is_test=True
        test_tenant = (await session.execute(
            select(Tenant).where(Tenant.id == "tenant-test-sandbox")
        )).scalar_one_or_none()
        
        if not test_tenant:
            test_tenant = Tenant(
                id="tenant-test-sandbox",
                name="Engineering Test Sandbox",
                slug="test-sandbox",
                is_test=True
            )
            session.add(test_tenant)
        else:
            test_tenant.is_test = True

        await session.flush()

        # 3. Locate or create rajababu user
        # Check existing raja@gmail.com, raja_babu_test, or rajababu@gmail.com
        raja_users = (await session.execute(
            select(User).where(
                User.email.in_([
                    "raja@gmail.com",
                    "rajababu@gmail.com",
                    "raja_babu_test@skillissue.ai",
                    "rajababu@skillissue.com",
                    "chowdhary.raja0607@gmail.com",
                ])
            )
        )).scalars().all()

        if raja_users:
            rajababu = raja_users[0]
            rajababu.email = "rajababu@gmail.com"
        else:
            rajababu = User(email="rajababu@gmail.com")
            session.add(rajababu)

        rajababu.hashed_password = hash_password("Password123!")
        rajababu.role = "admin"
        rajababu.tenant_id = "tenant-prod-default"
        rajababu.is_test = False
        rajababu.is_active = True
        rajababu.onboarding_completed = True

        await session.flush()

        # Ensure user profile for rajababu
        p_res = await session.execute(select(UserProfile).where(UserProfile.user_id == rajababu.id))
        profile = p_res.scalar_one_or_none()
        if not profile:
            profile = UserProfile(
                user_id=rajababu.id,
                target_role="Software Development Engineer (Full Stack & Systems)",
                years_experience=2.0,
                daily_study_minutes=60,
                bio="Competitive programmer & AI Systems Engineer"
            )
            session.add(profile)
        else:
            profile.target_role = "Software Development Engineer (Full Stack & Systems)"

        # 4. Move ALL other users in the entire database to is_test=True
        await session.execute(
            update(User)
            .where(User.id != rajababu.id)
            .values(is_test=True)
        )

        # 5. For users that were pointing to tenant-prod-default, move them to tenant-test-sandbox
        await session.execute(
            update(User)
            .where(User.id != rajababu.id, User.tenant_id == "tenant-prod-default")
            .values(tenant_id="tenant-test-sandbox")
        )

        # 6. Mark all other tenants as is_test=True except tenant-prod-default
        await session.execute(
            update(Tenant)
            .where(Tenant.id != "tenant-prod-default")
            .values(is_test=True)
        )

        await session.commit()

        # 7. Verify counts
        real_users_count = (await session.execute(
            select(func.count(User.id)).where(User.is_test == False)
        )).scalar_one()

        test_users_count = (await session.execute(
            select(func.count(User.id)).where(User.is_test == True)
        )).scalar_one()

        prod_tenant_users = (await session.execute(
            select(func.count(User.id)).where(User.tenant_id == "tenant-prod-default")
        )).scalar_one()

        print(f"✓ Production users (is_test=False): {real_users_count} (Expected: 1)")
        print(f"✓ Test & Sandbox users (is_test=True): {test_users_count}")
        print(f"✓ Users in 'tenant-prod-default': {prod_tenant_users} (Expected: 1)")
        print(f"✓ Single production user: id={rajababu.id}, email={rajababu.email}, role={rajababu.role}, is_test={rajababu.is_test}")

        assert real_users_count == 1, f"Expected exactly 1 production user, found {real_users_count}"
        assert prod_tenant_users == 1, f"Expected exactly 1 user in tenant-prod-default, found {prod_tenant_users}"

if __name__ == "__main__":
    asyncio.run(partition_database())
