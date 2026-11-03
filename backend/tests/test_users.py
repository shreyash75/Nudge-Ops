import pytest

from app.api.auth import _hash_password
from app.db.users import (
    DuplicateEmailError,
    UserRecord,
    create_user,
    get_user_by_email,
    get_user_by_id,
)


def test_create_and_fetch_user_roundtrip():
    password_hash = _hash_password("password123")

    created = create_user("ops@example.com", password_hash)
    assert isinstance(created, UserRecord)
    assert created.email == "ops@example.com"
    assert created.password_hash == password_hash
    assert created.id

    by_email = get_user_by_email("ops@example.com")
    assert by_email is not None
    assert by_email.id == created.id

    by_id = get_user_by_id(created.id)
    assert by_id is not None
    assert by_id.email == "ops@example.com"

    assert get_user_by_email("missing@example.com") is None
    assert get_user_by_id("nope") is None


def test_duplicate_email_raises():
    hashed = _hash_password("password123")
    create_user("dup@example.com", hashed)

    with pytest.raises(DuplicateEmailError):
        create_user("dup@example.com", hashed)
