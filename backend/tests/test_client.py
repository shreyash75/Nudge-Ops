import httpx
import pytest

from app.ai import client as llm_client
from app.ai.client import LLMClientError, request_completion


def _response(status_code=200, content="ok"):
    response = httpx.Response(
        status_code=status_code,
        request=httpx.Request("POST", llm_client.OPENROUTER_CHAT_URL),
    )
    if status_code == 200:
        response._content = (
            b'{"choices": [{"message": {"content": "' + content.encode() + b'"}}]}'
        )
    else:
        response._content = b'{"error": "boom"}'
    return response


@pytest.fixture(autouse=True)
def stub_settings(monkeypatch):
    monkeypatch.setattr(
        llm_client.settings, "openrouter_api_key", "test-key", raising=False
    )
    monkeypatch.setattr(
        llm_client.settings, "openrouter_model", "test-model", raising=False
    )
    monkeypatch.setattr(llm_client, "_wait_before_retry", lambda attempt: None)


def test_success_returns_content(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append(url)
        return _response(content="diagnosis json")

    monkeypatch.setattr(llm_client.httpx, "post", fake_post)

    assert request_completion([{"role": "user", "content": "x"}]) == "diagnosis json"
    assert len(calls) == 1


def test_retryable_failure_is_retried(monkeypatch):
    responses = [_response(500), _response(500), _response(content="final")]

    def fake_post(url, **kwargs):
        return responses.pop(0)

    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    assert request_completion([{"role": "user", "content": "x"}]) == "final"


def test_retries_exhausted_raises(monkeypatch):
    monkeypatch.setattr(llm_client.httpx, "post", lambda url, **kwargs: _response(500))
    with pytest.raises(LLMClientError):
        request_completion([{"role": "user", "content": "x"}])


def test_client_error_is_not_retried(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append(1)
        return _response(401)

    monkeypatch.setattr(llm_client.httpx, "post", fake_post)
    with pytest.raises(LLMClientError):
        request_completion([{"role": "user", "content": "x"}])
    assert len(calls) == 1


def test_missing_configuration_raises():
    llm_client.settings.openrouter_api_key = ""
    with pytest.raises(LLMClientError):
        request_completion([{"role": "user", "content": "x"}])
