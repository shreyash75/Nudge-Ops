import json
from datetime import datetime, timezone

import httpx
from loguru import logger

from app.core.config import settings
from app.models.schemas import InvestigateResponse


def _auth_headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.insforge_api_key}",
        "Content-Type": "application/json",
    }


def _table_url() -> str:
    table = settings.insforge_history_table
    return f"{settings.insforge_url.rstrip('/')}/api/database/records/{table}"


def save_investigation_history(user_id: str, response: InvestigateResponse) -> None:
    """Persist the completed investigation to the InsForge history table.

    The stored row is owned by the FastAPI-managed user ID; the request is
    made with the server API key because callers no longer carry InsForge
    tokens.
    """

    if not settings.insforge_url.strip() or not response.investigation_id:
        return

    diagnosis = response.diagnosis
    payload = {
        "id": response.investigation_id,
        "user_id": user_id,
        "cluster": response.cluster,
        "status": response.status,
        "message": response.message,
        "root_cause": (
            diagnosis.root_cause
            if diagnosis
            else (
                "No critical Kubernetes issues detected"
                if response.cluster_healthy
                else None
            )
        ),
        "namespace": diagnosis.namespace if diagnosis else None,
        "explanation": (
            diagnosis.explanation
            if diagnosis
            else (response.message if response.cluster_healthy else None)
        ),
        "confidence": diagnosis.confidence if diagnosis else None,
        "investigation": response.investigation.model_dump(mode="json"),
        "diagnosis": (
            diagnosis.model_dump(mode="json") if diagnosis is not None else None
        ),
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }

    try:
        with httpx.Client(timeout=10.0) as client:
            result = client.post(
                _table_url(),
                params={"on_conflict": "id"},
                headers=_auth_headers(),
                json=[payload],
            )
            result.raise_for_status()
    except httpx.HTTPError as exc:
        logger.error("Unable to save investigation history: {}", exc)


def load_investigation_history(user_id: str, email: str | None = None) -> list[dict]:
    """Return the user's saved investigations from InsForge, newest first.

    Investigations saved under the retired InsForge login system are owned by
    user IDs the FastAPI backend can never issue again. When the signed-in
    account has no rows yet, any legacy InsForge accounts with the same email
    are looked up and their rows are re-linked to this account, so users keep
    their pre-migration history.
    """

    if not settings.insforge_url.strip():
        return []

    rows = _fetch_history_rows(user_id)
    if rows or not email:
        return rows

    with httpx.Client(timeout=10.0) as client:
        legacy_user_ids = _lookup_legacy_user_ids(client, email)
        if not legacy_user_ids:
            return rows

        adopted = _adopt_legacy_rows(client, user_id, legacy_user_ids)
        if adopted:
            logger.info(
                "Re-linked {} investigation(s) from legacy InsForge accounts to {}",
                adopted,
                user_id,
            )
            return _fetch_history_rows(user_id, client)

    return rows


def _fetch_history_rows(
    user_id: str,
    client: httpx.Client | None = None,
) -> list[dict]:
    try:
        if client is not None:
            result = client.get(
                _table_url(),
                params=_history_query_params(user_id),
                headers=_auth_headers(),
            )
        else:
            with httpx.Client(timeout=10.0) as own_client:
                result = own_client.get(
                    _table_url(),
                    params=_history_query_params(user_id),
                    headers=_auth_headers(),
                )
        result.raise_for_status()
        rows = result.json() or []
        if not isinstance(rows, list):
            return []
        return [_normalize_row(row) for row in rows if isinstance(row, dict)]
    except (httpx.HTTPError, ValueError) as exc:
        logger.error("Unable to load investigation history: {}", exc)
        return []


def _history_query_params(user_id: str) -> dict[str, str]:
    return {
        "user_id": f"eq.{user_id}",
        "order": "created_at.desc",
        "limit": 25,
    }


def _lookup_legacy_user_ids(client: httpx.Client, email: str) -> list[str]:
    """Find pre-migration InsForge accounts registered with the same email."""

    try:
        result = client.get(
            f"{settings.insforge_url.rstrip('/')}/api/auth/users",
            params={"search": email, "limit": 10},
            headers=_auth_headers(),
        )
        result.raise_for_status()
        users = (result.json() or {}).get("data") or []
    except (httpx.HTTPError, ValueError) as exc:
        logger.error("Unable to look up legacy InsForge accounts: {}", exc)
        return []

    email = email.strip().lower()
    return [
        user["id"]
        for user in users
        if isinstance(user, dict)
        and isinstance(user.get("id"), str)
        and isinstance(user.get("email"), str)
        and user["email"].strip().lower() == email
    ]


def _adopt_legacy_rows(
    client: httpx.Client,
    user_id: str,
    legacy_user_ids: list[str],
) -> int:
    """Re-link rows saved under legacy accounts to the FastAPI-managed account."""

    adopted = 0
    for legacy_user_id in legacy_user_ids:
        if legacy_user_id == user_id:
            continue
        try:
            result = client.patch(
                _table_url(),
                params={"user_id": f"eq.{legacy_user_id}"},
                headers=_auth_headers(),
                json={"user_id": user_id},
            )
            result.raise_for_status()
            adopted += 1
        except httpx.HTTPError as exc:
            logger.error(
                "Unable to re-link history of legacy account {}: {}",
                legacy_user_id,
                exc,
            )
    return adopted


def _normalize_row(row: dict) -> dict:
    """Accept either created_at or createdAt style keys from the provider."""

    normalized = dict(row)
    normalized.setdefault("created_at", normalized.get("createdAt"))
    normalized.setdefault("completed_at", normalized.get("completedAt"))
    return normalized
