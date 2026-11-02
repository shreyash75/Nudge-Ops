from uuid import uuid4

import httpx
import pytest

import app.services.history as history_service
from app.core.config import settings
from app.models.schemas import (
    DeploymentsInvestigation,
    EventsInvestigation,
    InvestigateResponse,
    InvestigationPayload,
    LogsInvestigation,
    NetworkInvestigation,
    PodsInvestigation,
)
from app.services.history import (
    _normalize_row,
    load_investigation_history,
    save_investigation_history,
)

_RECORDS_URL = f"{settings.insforge_url.rstrip('/')}/api/database/records/investigation_history"
_USERS_URL = f"{settings.insforge_url.rstrip('/')}/api/auth/users"


class _FakeResponse:
    def __init__(self, body=None):
        self._body = body

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._body


class _FakeClient:
    """Returns canned responses; records every call."""

    def __init__(self, history_rows=None, search_users=None, fail=""):
        self._history_rows = history_rows
        self._search_users = search_users
        self.fail = fail  # "" | "get" | "post" | "patch"
        self.get_calls: list[dict] = []
        self.patch_calls: list[dict] = []
        self.post_call: dict | None = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def _connected(self, method: str) -> bool:
        return not (self.fail and self.fail.startswith(method))

    def get(self, url, **kwargs):
        self.get_calls.append({"url": url, **kwargs})
        if not self._connected("get"):
            raise httpx.ConnectError("boom")
        if url == _USERS_URL:
            return _FakeResponse(body=self._search_users)
        user_id = kwargs["params"]["user_id"].removeprefix("eq.")
        return _FakeResponse(
            body=[
                row
                for row in (self._history_rows or [])
                if isinstance(row, dict) and row.get("user_id") == user_id
            ]
        )

    def post(self, url, **kwargs):
        if not self._connected("post"):
            raise httpx.ConnectError("boom")
        self.post_call = {"url": url, **kwargs}
        return _FakeResponse()

    def patch(self, url, **kwargs):
        self.patch_calls.append({"url": url, **kwargs})
        if not self._connected("patch"):
            raise httpx.ConnectError("boom")
        legacy_user_id = kwargs["params"]["user_id"].removeprefix("eq.")
        new_user_id = kwargs["json"]["user_id"]
        self._history_rows = [
            {**row, "user_id": new_user_id} if row.get("user_id") == legacy_user_id else row
            for row in (self._history_rows or [])
        ]
        return _FakeResponse()


def _install(client):
    history_service.httpx.Client = lambda timeout=10.0: client


def _response() -> InvestigateResponse:
    return InvestigateResponse(
        investigation_id=str(uuid4()),
        cluster="prod",
        cluster_healthy=False,
        status="success",
        investigation=InvestigationPayload(
            pods=PodsInvestigation(healthy=False, total_pods=1),
            logs=LogsInvestigation(),
            events=EventsInvestigation(healthy=True),
            deployments=DeploymentsInvestigation(healthy=True),
            network=NetworkInvestigation(healthy=True),
        ),
    )


def test_save_posts_row_owned_by_backend_user(monkeypatch):
    client = _FakeClient()
    _install(client)

    save_investigation_history("user-123", _response())

    assert client.post_call["url"] == _RECORDS_URL
    payload = client.post_call["json"][0]
    assert payload["user_id"] == "user-123"
    assert payload["cluster"] == "prod"
    assert payload["status"] == "success"
    assert client.post_call["headers"]["Authorization"] == f"Bearer {settings.insforge_api_key}"
    assert client.post_call["params"]["on_conflict"] == "id"


def test_save_failure_is_swallowed(monkeypatch):
    client = _FakeClient(fail="post")
    _install(client)
    save_investigation_history("user-123", _response())


def test_save_skipped_without_insforge_url(monkeypatch):
    monkeypatch.setattr(settings, "insforge_url", "", raising=False)

    def _unexpected(timeout=10.0):
        raise AssertionError("client must not be created without insforge_url")

    monkeypatch.setattr(history_service.httpx, "Client", _unexpected)
    save_investigation_history("user-123", _response())
    monkeypatch.setattr(settings, "insforge_url", "https://z7zui5k9.us-east.insforge.app")


def test_load_filters_by_user_with_admin_headers(monkeypatch):
    rows = [
        {
            "id": "inv-1",
            "user_id": "user-123",
            "cluster": "prod",
            "status": "success",
            "createdAt": "2026-11-02T10:00:00+00:00",
        }
    ]
    client = _FakeClient(history_rows=rows)
    _install(client)

    result = load_investigation_history("user-123")

    assert len(client.get_calls) == 1
    called = client.get_calls[0]
    assert called["url"] == _RECORDS_URL
    assert called["params"]["user_id"] == "eq.user-123"
    assert called["params"]["order"] == "created_at.desc"
    assert called["params"]["limit"] == 25
    assert called["headers"]["Authorization"] == f"Bearer {settings.insforge_api_key}"
    normalized = result[0]
    assert normalized["id"] == "inv-1"
    assert normalized["created_at"] == "2026-11-02T10:00:00+00:00"
    assert normalized["completed_at"] is None


def test_load_failure_returns_empty_list(monkeypatch):
    client = _FakeClient(fail="get")
    _install(client)
    assert load_investigation_history("user-123") == []


def test_load_skipped_without_insforge_url(monkeypatch):
    monkeypatch.setattr(settings, "insforge_url", "", raising=False)
    assert load_investigation_history("user-123") == []
    monkeypatch.setattr(settings, "insforge_url", "https://z7zui5k9.us-east.insforge.app")


def test_normalize_row_falls_back_to_camel_case_keys():
    row = {"id": "inv-2", "completedAt": "2026-11-02T09:00:00+00:00"}
    normalized = _normalize_row(row)
    assert normalized["created_at"] is None
    assert normalized["completed_at"] == row["completedAt"]
    assert row == {"id": "inv-2", "completedAt": row["completedAt"]}


@pytest.mark.parametrize(
    "rows",
    ["not-a-list", None, [{"id": "inv-3", "user_id": "user-123"}, "junk", 123]],
)
def test_load_tolerates_malformed_rows(monkeypatch, rows):
    client = _FakeClient(history_rows=rows)
    _install(client)
    result = load_investigation_history("user-123")
    assert all(isinstance(row, dict) for row in result)
    if isinstance(rows, list):
        assert len(result) == 1
    else:
        assert result == []


def test_load_adopts_legacy_rows_when_user_has_none(monkeypatch):
    legacy_rows = [
        {
            "id": "legacy-inv-1",
            "user_id": "legacy-account-id",
            "cluster": "prod",
            "status": "success",
            "created_at": "2026-11-01T10:00:00+00:00",
        }
    ]
    search_users = {
        "data": [
            {"id": "legacy-account-id", "email": "Owner@Example.com"},
            {"id": "someone-else", "email": "other@Example.com"},
        ]
    }
    client = _FakeClient(history_rows=legacy_rows, search_users=search_users)
    _install(client)

    result = load_investigation_history("user-123", "owner@example.com")

    search_calls = [c for c in client.get_calls if c["url"] == _USERS_URL]
    assert len(search_calls) == 1
    assert search_calls[0]["params"]["search"] == "owner@example.com"
    assert search_calls[0]["headers"]["Authorization"] == f"Bearer {settings.insforge_api_key}"

    assert len(client.patch_calls) == 1
    patch_call = client.patch_calls[0]
    assert patch_call["url"] == _RECORDS_URL
    assert patch_call["params"]["user_id"] == "eq.legacy-account-id"
    assert patch_call["json"] == {"user_id": "user-123"}

    assert result[0]["id"] == "legacy-inv-1"


def test_load_does_not_adopt_when_rows_already_exist(monkeypatch):
    rows = [{"id": "own-1", "user_id": "user-123", "cluster": "prod", "status": "success"}]
    client = _FakeClient(history_rows=rows, search_users={"data": []})
    _install(client)

    result = load_investigation_history("user-123", "owner@example.com")

    assert client.patch_calls == []
    assert [c["url"] for c in client.get_calls] == [_RECORDS_URL]
    assert result[0]["id"] == "own-1"


def test_load_skips_adoption_without_email(monkeypatch):
    client = _FakeClient(history_rows=[])
    _install(client)
    result = load_investigation_history("user-123")
    assert result == []
    assert [c["url"] for c in client.get_calls] == [_RECORDS_URL]
    assert client.patch_calls == []


def test_load_no_adopt_when_no_legacy_account_matches_email(monkeypatch):
    search_users = {
        "data": [
            {"id": "other-id", "email": "other@else.com"},
        ]
    }
    client = _FakeClient(history_rows=[], search_users=search_users)
    _install(client)

    result = load_investigation_history("user-123", "owner@example.com")

    assert len([c for c in client.get_calls if c["url"] == _USERS_URL]) == 1
    assert client.patch_calls == []
    assert result == []


def test_load_ignores_search_failures(monkeypatch):
    client = _FakeClient(history_rows=[], search_users={"data": []}, fail="get")
    _install(client)
    assert load_investigation_history("user-123", "owner@example.com") == []
    assert len([c for c in client.get_calls if c["url"] == _USERS_URL]) == 1
    assert client.patch_calls == []


def test_load_ignores_patch_failures(monkeypatch):
    legacy_rows = [{"id": "legacy-inv", "user_id": "legacy-account-id", "status": "success"}]
    search_users = {"data": [{"id": "legacy-account-id", "email": "owner@example.com"}]}
    client = _FakeClient(history_rows=[], search_users=search_users, fail="patch")
    _install(client)

    assert load_investigation_history("user-123", "owner@example.com") == []
    assert len(client.patch_calls) == 1
