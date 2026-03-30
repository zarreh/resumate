"""Auth service — password hashing and JWT token management."""

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.models.user import RefreshToken, User

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())


def create_access_token(user_id: uuid.UUID) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": str(user_id), "exp": expire, "type": "access"}
    return jwt.encode(payload, settings.secret_key, algorithm=ALGORITHM)


def decode_access_token(token: str) -> uuid.UUID | None:
    """Decode an access token and return the user_id, or None if invalid."""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        if payload.get("type") != "access":
            return None
        user_id = payload.get("sub")
        if user_id is None:
            return None
        return uuid.UUID(user_id)
    except (JWTError, ValueError):
        return None


def _hash_refresh_token(token: str) -> str:
    """SHA-256 hash for storing refresh tokens."""
    return hashlib.sha256(token.encode()).hexdigest()


async def create_refresh_token(db: AsyncSession, user_id: uuid.UUID) -> str:
    """Generate a refresh token, store its hash in DB, return the raw token."""
    raw_token = secrets.token_urlsafe(64)
    token_hash = _hash_refresh_token(raw_token)
    expires_at = datetime.now(UTC) + timedelta(days=settings.refresh_token_expire_days)

    refresh = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    db.add(refresh)
    await db.commit()
    return raw_token


async def verify_refresh_token(db: AsyncSession, raw_token: str) -> User | None:
    """Verify a refresh token and return the associated user, or None."""
    token_hash = _hash_refresh_token(raw_token)
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.expires_at > datetime.now(UTC),
        )
    )
    refresh = result.scalar_one_or_none()
    if refresh is None:
        return None

    # Rotate: delete the used token
    await db.delete(refresh)
    await db.commit()

    result = await db.execute(select(User).where(User.id == refresh.user_id))
    return result.scalar_one_or_none()
