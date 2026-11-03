"""Shared PostgreSQL (or SQLite in tests) access for users and history."""

from threading import Lock

from sqlalchemy import (
    Index,
    JSON,
    MetaData,
    Table,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.dialects.postgresql import JSONB
from loguru import logger

from app.core.config import settings

metadata = MetaData()


def _json_column() -> JSON:
    return JSON().with_variant(JSONB, "postgresql")


app_users = Table(
    "app_users",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("email", String(320), nullable=False, unique=True),
    Column("password_hash", Text, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
)

investigation_history = Table(
    "investigation_history",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("user_id", String(36), nullable=False),
    Column("cluster", String(253)),
    Column("status", String(64), nullable=False),
    Column("message", Text),
    Column("root_cause", Text),
    Column("namespace", String(255)),
    Column("explanation", Text),
    Column("confidence", Integer),
    Column("investigation", _json_column(), nullable=False),
    Column("diagnosis", _json_column()),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("completed_at", DateTime(timezone=True)),
)

Index(
    "investigation_history_user_created_idx",
    investigation_history.c.user_id,
    investigation_history.c.created_at.desc(),
)

_engine = None
_schema_ready = False
_lock = Lock()


def _database_url() -> str:
    """Force the psycopg 3 dialect for plain PostgreSQL URLs.

    SQLAlchemy resolves bare ``postgresql://`` URLs to its psycopg2 dialect,
    so rewrite them to the explicit ``postgresql+psycopg://`` driver that
    matches the installed psycopg 3 package.
    """

    url = settings.database_url
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


def _engine_kwargs() -> dict:
    if _database_url().startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {}


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_engine(_database_url(), pool_pre_ping=True, **_engine_kwargs())
    return _engine


def ensure_schema() -> None:
    """Create the tables if they do not exist yet (idempotent)."""

    global _schema_ready
    if _schema_ready:
        return
    with _lock:
        if _schema_ready:
            return
        engine = get_engine()
        metadata.create_all(engine)
        logger.info(
            "Database schema ready ({})", engine.url.render_as_string(hide_password=True)
        )
        _schema_ready = True


def reset() -> None:
    """Reset the cached engine (used on startup and by tests)."""

    global _engine, _schema_ready
    with _lock:
        _engine = None
        _schema_ready = False
