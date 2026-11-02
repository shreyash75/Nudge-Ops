from collections import defaultdict
from typing import Any

from loguru import logger

from app.kubernetes.constants import EVENT_PROBLEM_REASONS, MAX_EVENT_FINDINGS
from app.kubernetes.executor import run_kubectl_json
from app.models.schemas import EventFinding, EventsInvestigation


def analyze_events(context: str | None = None) -> EventsInvestigation:
    """Summarize Kubernetes events that usually indicate failures."""

    payload, result = run_kubectl_json(["get", "events", "-A"], context=context)
    if payload is None:
        return EventsInvestigation(healthy=False, findings=[], error=result.error)

    findings = _summarize_events(payload.get("items") or [], MAX_EVENT_FINDINGS)

    logger.info("Events analyzer found {} summarized findings", len(findings))
    return EventsInvestigation(healthy=len(findings) == 0, findings=findings)


def _summarize_events(
    events: list[dict[str, Any]],
    max_findings: int,
) -> list[EventFinding]:
    grouped: dict[tuple[str, str, str], dict[str, Any]] = defaultdict(
        lambda: {"count": 0, "message": "", "last_seen": ""}
    )

    for event in events:
        reason = event.get("reason") or ""
        if reason not in EVENT_PROBLEM_REASONS:
            continue

        involved = event.get("involvedObject") or {}
        namespace = event.get("metadata", {}).get("namespace") or involved.get("namespace") or "default"
        object_name = involved.get("name") or "unknown"
        object_kind = involved.get("kind") or "Object"
        object_ref = f"{object_kind}/{object_name}"
        key = (namespace, object_ref, reason)
        grouped[key]["count"] += int(event.get("count") or 1)
        grouped[key]["message"] = event.get("message") or grouped[key]["message"]
        grouped[key]["last_seen"] = (
            event.get("lastTimestamp")
            or event.get("eventTime")
            or (event.get("metadata") or {}).get("creationTimestamp")
            or ""
        )

    findings = [
        EventFinding(
            reason=reason,
            count=data["count"],
            namespace=namespace,
            object=object_ref,
            message=data["message"],
            last_seen=data["last_seen"] or None,
        )
        for (namespace, object_ref, reason), data in grouped.items()
    ]
    findings.sort(key=lambda item: (item.namespace, item.object))
    findings.sort(key=lambda item: item.count, reverse=True)
    return findings[:max_findings]
