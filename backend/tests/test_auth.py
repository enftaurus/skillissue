import uuid
import pytest
import httpx
from backend.app.core.security import dummy_verify_password

@pytest.mark.asyncio
async def test_auth_workflow(client: httpx.AsyncClient):
    # 1. Health check
    health_res = await client.get("/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "healthy"

    # 2. Register user (only email and password per requirement)
    email = f"engineer_{uuid.uuid4().hex[:8]}@example.com"
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "SuperSecurePassword123!",
        }
    )
    assert reg_res.status_code == 201
    user_data = reg_res.json()
    assert user_data["email"] == email
    assert user_data["onboarding_completed"] is False
    assert user_data["is_provider_connected"] is False

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

    # 5. Login with non-existent email rejected
    non_existent = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "AnyPassword123!"}
    )
    assert non_existent.status_code == 401

    # 6. Login with valid password (sets access token and refresh token)
    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SuperSecurePassword123!"}
    )
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    token = token_data["access_token"]
    refresh_tok = token_data["refresh_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 7. Access /me with access token
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email

    # 8. Refresh session using refresh token
    ref_res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_tok}
    )
    assert ref_res.status_code == 200
    new_token_data = ref_res.json()
    assert "access_token" in new_token_data
    assert "refresh_token" in new_token_data
    new_token = new_token_data["access_token"]

    # 9. Logout user (revokes active session tokens)
    logout_res = await client.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {new_token}"}
    )
    assert logout_res.status_code == 200
    assert logout_res.json()["status"] == "logged_out"

    # 10. Previously issued access token must now be rejected (session revoked)
    revoked_res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {new_token}"}
    )
    assert revoked_res.status_code == 401

    # 11. Old refresh token must also be rejected
    bad_ref = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_tok}
    )
    assert bad_ref.status_code == 401

def test_dummy_bcrypt_constant_time():
    """Verify dummy verification executes safely without exception."""
    assert dummy_verify_password("Password123!") is False

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
