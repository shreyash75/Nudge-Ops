import pytest


@pytest.fixture(autouse=True)
def isolated_auth_settings(monkeypatch, tmp_path):
    """Keep auth secrets and the SQLite user store out of real files."""

    from app.core.config import settings
    from app.db import users

    monkeypatch.setattr(settings, "auth_secret", "unit-test-secret", raising=False)
    monkeypatch.setattr(
        settings, "auth_database_path", str(tmp_path / "unit-users.db"), raising=False
    )
    users._reset_schema_cache()
    yield
    users._reset_schema_cache()
