import bcrypt
from fastapi.testclient import TestClient

from app.api.auth import _hash_password, _verify_password
from app.core import auth as auth_module
from app.main import app

client = TestClient(app)


def test_password_hashing_roundtrip():
    hashed = _hash_password("s3cret-password")
    assert hashed != "s3cret-password"
    assert _verify_password("s3cret-password", hashed)
    assert not _verify_password("wrong", hashed)
    assert bcrypt.checkpw("s3cret-password".encode(), hashed.encode())


def test_register_creates_account_and_returns_token():
    email = "register-new@example.com"
    response = client.post(
        "/auth/register", json={"email": email, "password": "password123"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["access_token"]
    assert body["user"]["email"] == email
    assert body["user"]["id"]


def test_register_rejects_duplicate_email():
    payload = {"email": "dup@example.com", "password": "password123"}
    assert client.post("/auth/register", json=payload).status_code == 200
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


def test_register_rejects_weak_password_and_bad_email():
    weak = client.post(
        "/auth/register", json={"email": "ok@example.com", "password": "short"}
    )
    assert weak.status_code == 400
    bad_email = client.post(
        "/auth/register", json={"email": "not-an-email", "password": "password123"}
    )
    assert bad_email.status_code == 400


def test_login_accepts_correct_password_and_rejects_wrong():
    client.post(
        "/auth/register",
        json={"email": "login@example.com", "password": "password123"},
    )

    ok = client.post(
        "/auth/login", json={"email": "login@example.com", "password": "password123"}
    )
    assert ok.status_code == 200
    assert ok.json()["access_token"]

    wrong = client.post(
        "/auth/login", json={"email": "login@example.com", "password": "password456"}
    )
    assert wrong.status_code == 401

    unknown = client.post(
        "/auth/login", json={"email": "ghost@example.com", "password": "password123"}
    )
    assert unknown.status_code == 401


def test_expired_token_is_rejected(monkeypatch):
    monkeypatch.setattr(
        auth_module.settings,
        "auth_token_expire_minutes",
        -1,
        raising=False,
    )
    expired = auth_module.create_access_token("u-1", "me@example.com")
    response = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {expired}"}
    )
    assert response.status_code == 401


def test_tampered_token_is_rejected():
    valid = auth_module.create_access_token("u-1", "me@example.com")
    tampered = valid[:-4] + "zzzz"
    response = client.get(
        "/auth/me", headers={"Authorization": f"Bearer {tampered}"}
    )
    assert response.status_code == 401
