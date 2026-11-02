import re

import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from loguru import logger

from app.core.auth import AuthenticatedUser, create_access_token, require_authenticated_user
from app.db import users
from app.models.schemas import AuthRequest, AuthResponse, CurrentUser

router = APIRouter(tags=["authentication"])

_EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def _verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _auth_response(user: users.UserRecord) -> AuthResponse:
    return AuthResponse(
        access_token=create_access_token(user.id, user.email),
        user=CurrentUser(id=user.id, email=user.email),
    )


@router.post("/auth/register", response_model=AuthResponse)
def register_account(request: AuthRequest) -> AuthResponse:
    """Create a backend-managed account and sign the user in immediately."""

    email = request.email.strip()
    _validate_email(email)
    _validate_password(request.password)

    try:
        user = users.create_user(email, _hash_password(request.password))
    except users.DuplicateEmailError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email already exists. Please sign in.",
        ) from None

    logger.info("User registered: {}", user.email)
    return _auth_response(user)


@router.post("/auth/login", response_model=AuthResponse)
def login(request: AuthRequest) -> AuthResponse:
    """Sign in with email and password."""

    user = users.get_user_by_email(request.email)
    if user is None or not _verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    return _auth_response(user)


@router.get("/auth/me", response_model=CurrentUser)
def current_session(user: AuthenticatedUser = Depends(require_authenticated_user)) -> CurrentUser:
    """Return the account that owns the bearer token."""

    return CurrentUser(id=user.id, email=user.email)


def _validate_email(email: str) -> None:
    if not _EMAIL_PATTERN.fullmatch(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid email address.",
        )


def _validate_password(password: str) -> None:
    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long.",
        )
