import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

from app.core.config import settings
from loguru import logger

_SCHEMA = """
create table if not exists app_users (
  id text primary key,
  email text not null unique,
  password_hash text not null,
  created_at text not null
)
"""

_schema_lock = threading.Lock()
_schema_ready = False


class DuplicateEmailError(Exception):
    """Raised when a user registers an email that already exists."""


class UserRecord:
    """A backend-managed user account."""

    def __init__(self, id: str, email: str, password_hash: str) -> None:
        self.id = id
        self.email = email
        self.password_hash = password_hash


def _connect() -> sqlite3.Connection:
    path = Path(settings.auth_database_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def _ensure_schema(connection: sqlite3.Connection) -> None:
    global _schema_ready
    if _schema_ready:
        return
    with _schema_lock:
        if not _schema_ready:
            connection.executescript(_SCHEMA)
            connection.commit()
            logger.info("Backend user store initialized at {}", settings.auth_database_path)
            _schema_ready = True


def _reset_schema_cache() -> None:
    global _schema_ready
    with _schema_lock:
        _schema_ready = False


def create_user(email: str, password_hash: str) -> UserRecord:
    """Create a backend-managed user and return the stored record."""

    email = email.strip().lower()
    record = UserRecord(str(uuid.uuid4()), email, password_hash)

    connection = _connect()
    try:
        _ensure_schema(connection)
        connection.execute(
            "insert into app_users (id, email, password_hash, created_at) values (?, ?, ?, ?)",
            (
                record.id,
                record.email,
                record.password_hash,
                datetime.now(timezone.utc).isoformat(),
            ),
        )
        connection.commit()
    except sqlite3.IntegrityError as exc:
        raise DuplicateEmailError(email) from exc
    finally:
        connection.close()

    logger.info("Created backend user {}", record.id)
    return record


def get_user_by_email(email: str) -> UserRecord | None:
    connection = _connect()
    try:
        _ensure_schema(connection)
        row = connection.execute(
            "select id, email, password_hash from app_users where email = ?",
            (email.strip().lower(),),
        ).fetchone()
    finally:
        connection.close()

    if row is None:
        return None
    return UserRecord(row["id"], row["email"], row["password_hash"])


def get_user_by_id(user_id: str) -> UserRecord | None:
    connection = _connect()
    try:
        _ensure_schema(connection)
        row = connection.execute(
            "select id, email, password_hash from app_users where id = ?",
            (user_id,),
        ).fetchone()
    finally:
        connection.close()

    if row is None:
        return None
    return UserRecord(row["id"], row["email"], row["password_hash"])
