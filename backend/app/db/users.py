import uuid
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from loguru import logger

from app.db import database
from app.db.database import app_users


class DuplicateEmailError(Exception):
    """Raised when a user registers an email that already exists."""


class UserRecord:
    """A backend-managed user account."""

    def __init__(self, id: str, email: str, password_hash: str) -> None:
        self.id = id
        self.email = email
        self.password_hash = password_hash


def create_user(email: str, password_hash: str) -> UserRecord:
    """Create a backend-managed user and return the stored record."""

    email = email.strip().lower()
    record = UserRecord(str(uuid.uuid4()), email, password_hash)

    database.ensure_schema()
    try:
        with database.get_engine().begin() as connection:
            connection.execute(
                app_users.insert().values(
                    id=record.id,
                    email=record.email,
                    password_hash=record.password_hash,
                    created_at=datetime.now(timezone.utc),
                )
            )
    except IntegrityError as exc:
        raise DuplicateEmailError(email) from exc

    logger.info("Created backend user {}", record.id)
    return record


def get_user_by_email(email: str) -> UserRecord | None:
    database.ensure_schema()
    with database.get_engine().connect() as connection:
        row = connection.execute(
            app_users.select().where(app_users.c.email == email.strip().lower())
        ).mappings().first()

    if row is None:
        return None
    return UserRecord(row["id"], row["email"], row["password_hash"])


def get_user_by_id(user_id: str) -> UserRecord | None:
    database.ensure_schema()
    with database.get_engine().connect() as connection:
        row = connection.execute(
            app_users.select().where(app_users.c.id == user_id)
        ).mappings().first()

    if row is None:
        return None
    return UserRecord(row["id"], row["email"], row["password_hash"])
