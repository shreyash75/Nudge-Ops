import pytest


@pytest.fixture(autouse=True)
def isolated_database(monkeypatch, tmp_path):
    """Point the app at a throwaway database and auth secret per test."""

    from app.core.config import settings
    from app.db import database

    monkeypatch.setattr(
        settings,
        "database_url",
        f"sqlite:///{(tmp_path / 'nudgeops-test.db').as_posix()}",
        raising=False,
    )
    monkeypatch.setattr(settings, "auth_secret", "unit-test-secret", raising=False)
    monkeypatch.setattr(
        settings, "jwt_secret_path", str(tmp_path / "jwt-secret.key"), raising=False
    )
    database.reset()
    yield
    database.reset()
