import secrets
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger

from app.core.config import settings

bearer_scheme = HTTPBearer(auto_error=False)

_ALGORITHM = "HS256"


@dataclass(frozen=True)
class AuthenticatedUser:
    id: str
    email: str | None = None
    access_token: str = field(default="", repr=False)


def _resolve_secret() -> bytes:
    """Return the JWT signing secret, creating a stable one if unconfigured."""

    if settings.auth_secret.strip():
        return settings.auth_secret.strip().encode()

    path = Path(settings.jwt_secret_path)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            return path.read_text(encoding="utf-8").strip().encode()
        secret = secrets.token_hex(32)
        path.write_text(secret, encoding="utf-8")
        logger.info("Generated a new JWT signing secret at {}", path)
        return secret.encode()
    except OSError as exc:
        logger.error("Unable to persist the JWT signing secret: {}", exc)
        return secrets.token_hex(32).encode()


def create_access_token(user_id: str, email: str | None) -> str:
    """Issue a signed FastAPI-managed session token."""

    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.auth_token_expire_minutes)).timestamp()),
    }
    return jwt.encode(payload, _resolve_secret(), algorithm=_ALGORITHM)


def decode_access_token(token: str) -> AuthenticatedUser:
    """Validate a session token and return the authenticated user."""

    try:
        payload = jwt.decode(token, _resolve_secret(), algorithms=[_ALGORITHM])
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication session",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token did not include a user",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return AuthenticatedUser(
        id=str(user_id),
        email=payload.get("email"),
        access_token=token,
    )


def require_authenticated_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> AuthenticatedUser:
    """Validate the FastAPI-managed bearer token of the caller."""

    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return decode_access_token(credentials.credentials)
