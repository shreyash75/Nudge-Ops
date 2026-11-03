from fastapi.testclient import TestClient

from app.core.auth import AuthenticatedUser, require_authenticated_user
from app.main import app

client = TestClient(app)


def _authenticate_as(user_id: str) -> None:
    app.dependency_overrides[require_authenticated_user] = lambda: AuthenticatedUser(
        id=user_id
    )


def _clear_authentication() -> None:
    app.dependency_overrides.pop(require_authenticated_user, None)


def teardown_function() -> None:
    _clear_authentication()


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "nudgeops"}


def test_clusters_require_authentication():
    response = client.get("/clusters")
    assert response.status_code == 401


def test_investigate_requires_authentication():
    response = client.post("/investigate", json={"cluster": "prod"})
    assert response.status_code == 401


def test_invalid_bearer_token_returns_401():
    response = client.get("/clusters", headers={"Authorization": "Bearer garbage"})
    assert response.status_code == 401


def test_auth_me_returns_registered_account():
    register = client.post(
        "/auth/register",
        json={"email": "api-me@example.com", "password": "password123"},
    )
    assert register.status_code == 200
    token = register.json()["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["email"] == "api-me@example.com"


def test_history_endpoint_returns_saved_rows(monkeypatch):
    import app.api.history as history_api

    _authenticate_as("user-123")
    saved_rows = [
        {
            "id": "inv-1",
            "user_id": "user-123",
            "cluster": "prod",
            "status": "success",
            "created_at": "2026-11-02T10:00:00+00:00",
        }
    ]
    monkeypatch.setattr(
        history_api,
        "load_investigation_history",
        lambda user_id: saved_rows,
    )
    response = client.get("/investigate/history")
    assert response.status_code == 200
    assert response.json() == saved_rows


def test_progress_stream_requires_valid_token():
    response = client.get(
        "/investigate/progress/inv-x?token=not-a-real-token"
    )
    assert response.status_code == 401


def test_progress_stream_replays_buffered_events_and_stops_on_completed():
    import asyncio

    from app.core import auth as auth_module
    from app.services.progress import InvestigationProgressPublisher

    publisher = InvestigationProgressPublisher(investigation_id="inv-sse")
    publisher.publish("gather-evidence", "running", "Collecting evidence")
    publisher.publish("completed", "completed", "Investigation complete")

    token = auth_module.create_access_token("user-1", "me@example.com")

    async def call_sse() -> tuple[int, str, bytes]:
        # stream-client helpers (TestClient/ASGITransport) buffer streamed
        # bodies with the current starlette/httpx pairing, so speak ASGI
        # directly for this endpoint.
        scope = {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "method": "GET",
            "scheme": "http",
            "path": "/investigate/progress/inv-sse",
            "raw_path": b"/investigate/progress/inv-sse",
            "query_string": f"token={token}".encode(),
            "headers": [],
            "client": ("test", 123),
            "server": ("test", 80),
        }
        request_started = False
        headers: dict = {}
        status_code = 0
        body = bytearray()

        async def receive():
            nonlocal request_started
            if not request_started:
                request_started = True
                return {"type": "http.request", "body": b"", "more_body": False}
            await asyncio.sleep(0.05)
            return {"type": "http.disconnect"}

        async def send(message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
                headers.update(
                    {
                        key.decode(): value.decode()
                        for key, value in message.get("headers", [])
                    }
                )
            if message["type"] == "http.response.body":
                body.extend(message.get("body", b""))

        await asyncio.wait_for(app(scope, receive, send), timeout=10)
        return status_code, headers.get("content-type", ""), bytes(body)

    status_code, content_type, body = asyncio.run(call_sse())

    assert status_code == 200
    assert content_type.startswith("text/event-stream")
    assert b'"stage": "gather-evidence"' in body
    assert b'"stage": "completed"' in body


def test_unknown_cluster_context_is_rejected(monkeypatch):
    import app.api.investigate as investigate_api

    _authenticate_as("user-123")
    monkeypatch.setattr(investigate_api, "current_context", lambda: None)
    monkeypatch.setattr(
        investigate_api,
        "cluster_context_exists",
        lambda cluster: (
            False,
            "The selected Kubernetes cluster is no longer available in the kubeconfig. "
            "Refresh the cluster list and try again.",
        ),
    )
    response = client.post(
        "/investigate",
        json={"cluster": "ghost"},
        headers={"Authorization": "Bearer token"},
    )
    assert response.status_code == 400
    assert "no longer available" in response.json()["detail"]
