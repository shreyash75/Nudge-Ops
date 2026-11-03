from datetime import datetime, timezone

from loguru import logger
from sqlalchemy import select

from app.db import database
from app.db.database import investigation_history
from app.models.schemas import InvestigateResponse

_HISTORY_LIMIT = 25


def save_investigation_history(user_id: str, response: InvestigateResponse) -> None:
    """Persist the completed investigation to PostgreSQL, owned by its user."""

    if not response.investigation_id:
        return

    diagnosis = response.diagnosis
    saved_at = datetime.now(timezone.utc)
    values = {
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
        "created_at": saved_at,
        "completed_at": saved_at,
    }

    try:
        database.ensure_schema()
        history_table = investigation_history
        with database.get_engine().begin() as connection:
            existing = connection.execute(
                select(history_table.c.id).where(history_table.c.id == values["id"])
            ).scalar()
            if existing is None:
                connection.execute(history_table.insert().values(**values))
            else:
                connection.execute(
                    history_table.update()
                    .where(history_table.c.id == values["id"])
                    .values(**values)
                )
    except Exception as exc:
        logger.error("Unable to save investigation history: {}", exc)


def load_investigation_history(user_id: str) -> list[dict]:
    """Return the user's saved investigations from PostgreSQL, newest first."""

    try:
        database.ensure_schema()
        with database.get_engine().connect() as connection:
            rows = connection.execute(
                select(investigation_history)
                .where(investigation_history.c.user_id == user_id)
                .order_by(investigation_history.c.created_at.desc())
                .limit(_HISTORY_LIMIT)
            ).mappings().all()
        return [dict(row) for row in rows]
    except Exception as exc:
        logger.error("Unable to load investigation history: {}", exc)
        return []
