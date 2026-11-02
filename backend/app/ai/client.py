import time

import httpx
from loguru import logger

from app.core.config import settings

OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
REQUEST_TIMEOUT_SECONDS = 60.0
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 1.0
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class LLMClientError(Exception):
    """Raised when the LLM request cannot produce a usable response."""


def request_completion(messages: list[dict[str, str]]) -> str:
    """Send chat messages to OpenRouter and return the raw assistant response."""

    api_key = settings.openrouter_api_key.strip()
    model = settings.openrouter_model.strip()

    if not api_key:
        raise LLMClientError("OPENROUTER_API_KEY is not configured")
    if not model:
        raise LLMClientError("OPENROUTER_MODEL is not configured")

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "X-Title": "NudgeOps",
    }

    last_error: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = httpx.post(
                OPENROUTER_CHAT_URL,
                headers=headers,
                json=payload,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )

            if response.status_code in RETRYABLE_STATUS_CODES:
                last_error = LLMClientError(
                    f"OpenRouter returned retryable HTTP {response.status_code}"
                )
                logger.warning(
                    "OpenRouter attempt {}/{} failed with HTTP {}",
                    attempt,
                    MAX_RETRIES,
                    response.status_code,
                )
                _wait_before_retry(attempt)
                continue

            response.raise_for_status()
            data = response.json()
            content = data["choices"][0]["message"]["content"]

            if not isinstance(content, str) or not content.strip():
                raise LLMClientError("OpenRouter returned an empty response")

            logger.info("OpenRouter diagnosis received with model {}", model)
            return content

        except httpx.TimeoutException as exc:
            last_error = exc
            logger.warning(
                "OpenRouter attempt {}/{} timed out after {} seconds",
                attempt,
                MAX_RETRIES,
                REQUEST_TIMEOUT_SECONDS,
            )
        except httpx.RequestError as exc:
            last_error = exc
            logger.warning(
                "OpenRouter attempt {}/{} could not connect: {}",
                attempt,
                MAX_RETRIES,
                type(exc).__name__,
            )
        except httpx.HTTPStatusError as exc:
            last_error = exc
            logger.error(
                "OpenRouter returned HTTP {} on attempt {}/{}",
                exc.response.status_code,
                attempt,
                MAX_RETRIES,
            )
            if exc.response.status_code < 500:
                break
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            last_error = exc
            logger.error(
                "OpenRouter returned an unexpected response on attempt {}/{}: {}",
                attempt,
                MAX_RETRIES,
                type(exc).__name__,
            )

        _wait_before_retry(attempt)

    raise LLMClientError(f"OpenRouter request failed: {last_error}")


def _wait_before_retry(attempt: int) -> None:
    if attempt >= MAX_RETRIES:
        return
    time.sleep(RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1)))
