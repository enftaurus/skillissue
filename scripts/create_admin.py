#!/usr/bin/env python3
"""
scripts/create_admin.py

Provisions or promotes a platform administrator in Skill Issue.
Admins can NEVER be registered over HTTP.

Usage:
    python3 scripts/create_admin.py --email admin@domain.com --password SecurePassword123!
    
    Or via environment variables:
    ADMIN_EMAIL=admin@domain.com ADMIN_PASSWORD=SecurePassword123! python3 scripts/create_admin.py
"""

import argparse
import asyncio
import os
import sys
from sqlalchemy import select

# Ensure backend is on PYTHONPATH
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.database.session import AsyncSessionLocal
from backend.app.database.models import User, UserProfile, ProviderConfig, Tenant
from backend.app.core.security import hash_password
from backend.app.providers.models_catalog import DEFAULT_MODEL_ID

async def create_or_promote_admin(email: str, password: str) -> None:
    email = email.lower().strip()
    if not email or "@" not in email:
        print("[ERROR] A valid email address is required.")
        sys.exit(1)
    if not password or len(password) < 8:
        print("[ERROR] Password must be at least 8 characters.")
        sys.exit(1)

    async with AsyncSessionLocal() as db:
        # Ensure default production tenant exists
        tenant_res = await db.execute(select(Tenant).where(Tenant.id == "tenant-prod-default"))
        default_tenant = tenant_res.scalar_one_or_none()
        if not default_tenant:
            default_tenant = Tenant(
                id="tenant-prod-default",
                name="Production Candidates",
                slug="default",
                is_test=False
            )
            db.add(default_tenant)
            await db.flush()

        # Check if user already exists
        user_res = await db.execute(select(User).where(User.email == email))
        user = user_res.scalar_one_or_none()

        if user:
            print(f"[INFO] User '{email}' already exists. Promoting to admin...")
            user.role = "admin"
            user.hashed_password = hash_password(password)
            user.is_active = True
            user.is_test = False
            if not user.tenant_id:
                user.tenant_id = "tenant-prod-default"
            await db.commit()
            print(f"[SUCCESS] User '{email}' promoted to platform administrator (role=admin).")
            return

        print(f"[INFO] Creating new platform administrator '{email}'...")
        admin_user = User(
            email=email,
            hashed_password=hash_password(password),
            role="admin",
            tenant_id="tenant-prod-default",
            is_test=False,
            is_active=True,
            onboarding_completed=True,
            token_version=1
        )
        db.add(admin_user)
        await db.flush()

        profile = UserProfile(
            user_id=admin_user.id,
            target_role="Platform Administrator",
            years_experience=0.0,
            daily_study_minutes=0,
        )
        db.add(profile)

        config = ProviderConfig(
            user_id=admin_user.id,
            provider_name="mock",
            aws_region="us-east-1",
            preferred_model=DEFAULT_MODEL_ID,
            default_model=DEFAULT_MODEL_ID,
            is_valid=True
        )
        db.add(config)

        await db.commit()
        print(f"[SUCCESS] Admin account created successfully for '{email}'.")

def main():
    parser = argparse.ArgumentParser(description="Create or promote an administrator for Skill Issue.")
    parser.add_argument("--email", default=os.environ.get("ADMIN_EMAIL"), help="Admin email address (or ADMIN_EMAIL env var)")
    parser.add_argument("--password", default=os.environ.get("ADMIN_PASSWORD"), help="Admin password (or ADMIN_PASSWORD env var)")
    args = parser.parse_args()

    if not args.email or not args.password:
        parser.print_help()
        print("\n[ERROR] Both --email and --password must be provided via CLI arguments or environment variables.")
        sys.exit(1)

    asyncio.run(create_or_promote_admin(args.email, args.password))

if __name__ == "__main__":
    main()
