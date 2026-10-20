import base64
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional, Union
import bcrypt
from jose import jwt
from cryptography.fernet import Fernet, InvalidToken
from backend.app.core.config import settings

ALGORITHM = "HS256"

# Pre-computed bcrypt hash of a random string for constant-time checks on missing emails
DUMMY_BCRYPT_HASH = "$2b$12$e80yvEegmFzM9e4Y1nNgeO7Y6R04w9f1K7mU15h0aBvV4B9xH5t0y"

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt(rounds=12)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def dummy_verify_password(plain_password: str) -> bool:
    """Perform a constant-time dummy verification to defeat timing attacks on email enumeration."""
    try:
        bcrypt.checkpw(plain_password.encode("utf-8"), DUMMY_BCRYPT_HASH.encode("utf-8"))
    except Exception:
        pass
    return False

def create_access_token(
    subject: Union[str, Any],
    token_version: int = 1,
    expires_delta: Optional[timedelta] = None
) -> str:
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    payload = {
        "exp": expire,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "sub": str(subject),
        "token_version": token_version,
        "token_type": "access",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)

def create_refresh_token(
    subject: Union[str, Any],
    token_version: int = 1,
    expires_delta: Optional[timedelta] = None
) -> str:
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    payload = {
        "exp": expire,
        "iat": now,
        "jti": str(uuid.uuid4()),
        "sub": str(subject),
        "token_version": token_version,
        "token_type": "refresh",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)

def decode_access_token(token: str) -> Optional[dict]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
    except Exception:
        return None

def _get_base_fernet() -> Fernet:
    raw_key = settings.ENCRYPTION_KEY
    if isinstance(raw_key, str):
        raw_key = raw_key.encode("utf-8")
    try:
        return Fernet(raw_key)
    except Exception:
        derived = base64.urlsafe_b64encode(hashlib.sha256(raw_key).digest())
        return Fernet(derived)

def get_user_fernet(user_id: str) -> Fernet:
    """
    Derive a tenant-isolated Data Encryption Key (DEK) per user using HKDF-style key derivation.
    This prevents any single leaked credential or key from decrypting data across multiple tenants.
    """
    master_key = settings.ENCRYPTION_KEY.encode("utf-8")
    salt = user_id.encode("utf-8")
    # HKDF-extract and expand using sha256
    derived_bytes = hashlib.pbkdf2_hmac("sha256", master_key, salt, iterations=10000, dklen=32)
    url_safe_key = base64.urlsafe_b64encode(derived_bytes)
    return Fernet(url_safe_key)

def encrypt_secret(plaintext: str, user_id: Optional[str] = None) -> str:
    if not plaintext:
        return ""
    if user_id:
        fernet = get_user_fernet(user_id)
    else:
        fernet = _get_base_fernet()
    return fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")

def decrypt_secret(ciphertext: str, user_id: Optional[str] = None) -> str:
    if not ciphertext:
        return ""
    
    if user_id:
        # Try per-user derived key first
        try:
            fernet = get_user_fernet(user_id)
            return fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
        except InvalidToken:
            # Fall back to base Fernet in case of legacy records
            pass

    fernet = _get_base_fernet()
    return fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")

def mask_access_key(key: str) -> str:
    if not key or len(key) <= 6:
        return "******"
    prefix = key[:4]
    suffix = key[-4:]
    return f"{prefix}...{suffix}"
