import uuid
import pytest
import httpx

@pytest.mark.asyncio
async def test_auth_workflow(client: httpx.AsyncClient):
    # 1. Health check
    health_res = await client.get("/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "healthy"

    # 2. Register user
    email = f"engineer_{uuid.uuid4().hex[:8]}@example.com"
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SuperSecurePassword123!",
            "target_role": "Backend Engineer",
            "years_experience": 2.5,
            "daily_study_minutes": 45
        }
    )
    assert reg_res.status_code == 201
    user_data = reg_res.json()
    assert user_data["email"] == email
    assert user_data["profile"]["target_role"] == "Backend Engineer"

    # 3. Duplicate registration rejected
    dup_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "AnotherPassword123!",
        }
    )
    assert dup_res.status_code == 400
    assert dup_res.json()["error"]["code"] == "EMAIL_ALREADY_EXISTS"

    # 4. Login with bad password rejected
    bad_login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "WrongPassword!"}
    )
    assert bad_login.status_code == 401

    # 5. Login with valid password
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SuperSecurePassword123!"}
    )
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 6. Get me
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email

    # 7. Update profile
    prof_res = await client.put(
        "/api/v1/auth/profile",
        headers=headers,
        json={"target_role": "Staff Distributed Systems Engineer", "daily_study_minutes": 60}
    )
    assert prof_res.status_code == 200
    assert prof_res.json()["target_role"] == "Staff Distributed Systems Engineer"
    assert prof_res.json()["daily_study_minutes"] == 60

    # 8. Delete account
    del_res = await client.delete("/api/v1/auth/account", headers=headers)
    assert del_res.status_code == 200

    # 9. Verify token no longer accesses /me
    after_del = await client.get("/api/v1/auth/me", headers=headers)
    assert after_del.status_code == 401

def test_production_secrets_validation():
    """Verify that Settings raises a validation error when production boots with default/weak secrets."""
    from backend.app.core.config import Settings
    
    # Insecure default secret in production must fail
    with pytest.raises(ValueError, match="Insecure or default SECRET_KEY rejected in production"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="dev-insecure-secret-key-at-least-32-chars-long!",
            ENCRYPTION_KEY="6nvbNYqsN6cT89ORW_FdvzG6F0jiE3dGo9L4W9ZthWs="
        )

    # Insecure default encryption key in production must fail
    with pytest.raises(ValueError, match="Insecure default ENCRYPTION_KEY rejected in production"):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="a-very-long-and-secure-random-production-secret-key-32chars!",
            ENCRYPTION_KEY="gH7_mK9_sP2_wL4_xR8_yT1_bV3_nQ6_zC5_dF0_jA="
        )

