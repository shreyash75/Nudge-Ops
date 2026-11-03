from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import sqlalchemy as sa

import app.db.database as database
import app.services.history as history_service
from app.db.database import investigation_history
from app.models.schemas import (
    DeploymentsInvestigation,
    EventsInvestigation,
    InvestigateResponse,
    InvestigationPayload,
    LogsInvestigation,
    NetworkInvestigation,
    PodsInvestigation,
)
from app.services.history import load_investigation_history, save_investigation_history


def _response(status: str = "success", message: str | None = None) -> InvestigateResponse:
    return InvestigateResponse(
        investigation_id=str(uuid4()),
        cluster="prod",
        cluster_healthy=status == "success",
        status=status,
        message=message,
        investigation=InvestigationPayload(
            pods=PodsInvestigation(healthy=False, total_pods=1),
            logs=LogsInvestigation(),
            events=EventsInvestigation(healthy=True),
            deployments=DeploymentsInvestigation(healthy=True),
            network=NetworkInvestigation(healthy=True),
        ),
    )


def _insert_row(row: dict) -> None:
    database.ensure_schema()
    with database.get_engine().begin() as connection:
        connection.execute(investigation_history.insert().values(**row))


def test_save_persists_row_owned_by_user():
    response = _response(message="Investigation finished")
    save_investigation_history("user-123", response)

    result = load_investigation_history("user-123")
    assert len(result) == 1
    row = result[0]
    assert row["id"] == response.investigation_id
    assert row["user_id"] == "user-123"
    assert row["cluster"] == "prod"
    assert row["status"] == "success"
    assert row["message"] == "Investigation finished"
    assert row["root_cause"] == "No critical Kubernetes issues detected"
    assert row["completed_at"] is not None
    assert isinstance(row["investigation"], dict)


def _broken_engine():
    raise RuntimeError("db down")


def test_save_failure_is_swallowed(monkeypatch):
    monkeypatch.setattr(history_service.database, "get_engine", _broken_engine)
    save_investigation_history("user-123", _response())


def test_load_returns_empty_list_when_user_has_no_rows():
    save_investigation_history("user-123", _response())
    assert load_investigation_history("other-user") == []


def test_load_failure_returns_empty_list(monkeypatch):
    monkeypatch.setattr(history_service.database, "get_engine", _broken_engine)
    assert load_investigation_history("user-123") == []


def test_save_upserts_on_same_investigation_id():
    response = _response()
    save_investigation_history("user-123", response)
    save_investigation_history("user-123", response)

    with database.get_engine().connect() as connection:
        count = connection.execute(
            sa.select(sa.func.count()).select_from(investigation_history)
        ).scalar()
    assert count == 1


def test_load_orders_newest_first_and_limits_25():
    now = datetime.now(timezone.utc)
    for index in range(27):
        _insert_row(
            {
                "id": f"inv-{index}",
                "user_id": "user-123",
                "cluster": "prod",
                "status": "success",
                "investigation": {},
                "created_at": now + timedelta(minutes=index),
                "completed_at": now + timedelta(minutes=index),
            }
        )

    result = load_investigation_history("user-123")
    assert len(result) == 25
    assert result[0]["id"] == "inv-26"
    assert result[-1]["id"] == "inv-2"
