import re
from typing import Any

from app.models.schemas import InvestigationPayload


def calculate_confidence(
    data: dict[str, Any],
    investigation: InvestigationPayload,
) -> tuple[int, list[str]]:
    """Normalize the confidence score and ensure reasoning is available."""

    confidence = _extract_confidence(data.get("confidence"))
    reasoning = _extract_reasoning(data.get("confidence_reasoning"))

    if confidence is None:
        confidence = _fallback_confidence(investigation)
    if not reasoning:
        reasoning = _evidence_reasoning(investigation)
    if not reasoning:
        reasoning = ["Limited evidence was available for this diagnosis."]

    return confidence, reasoning


def _extract_confidence(value: Any) -> int | None:
    if isinstance(value, bool):
        return None

    if isinstance(value, (int, float)):
        return _clamp(int(round(value)))

    if isinstance(value, str):
        match = re.search(r"-?\d+(?:\.\d+)?", value)
        if match:
            return _clamp(int(round(float(match.group()))))

    return None


def _extract_reasoning(value: Any) -> list[str]:
    if isinstance(value, list):
        return [_as_text(item) for item in value if _as_text(item)]

    if isinstance(value, str):
        lines = [line.strip(" -") for line in value.splitlines()]
        return [line for line in lines if line]

    return []


def _fallback_confidence(investigation: InvestigationPayload) -> int:
    signal_count = _signal_count(investigation)
    if signal_count >= 3:
        return 85
    if signal_count == 2:
        return 75
    if signal_count == 1:
        return 65
    return 40


def _signal_count(investigation: InvestigationPayload) -> int:
    return sum(
        [
            1 if investigation.pods.problematic_pods else 0,
            1 if any(item.highlights for item in investigation.logs.items) else 0,
            1 if investigation.events.findings else 0,
            1 if investigation.deployments.unhealthy_deployments else 0,
            1 if investigation.network.issues else 0,
        ]
    )


def _evidence_reasoning(investigation: InvestigationPayload) -> list[str]:
    reasons: list[str] = []

    if investigation.pods.problematic_pods:
        pod = investigation.pods.problematic_pods[0]
        reasons.append(
            f"{len(investigation.pods.problematic_pods)} problematic pod(s) detected, "
            f"including {pod.status} on {pod.namespace}/{pod.name}."
        )

    logged_pods = [item for item in investigation.logs.items if item.highlights]
    if logged_pods:
        item = logged_pods[0]
        reasons.append(
            f"Logs contained failure-related lines for {len(logged_pods)} pod(s), "
            f"including {item.namespace}/{item.name}."
        )

    if investigation.events.findings:
        event = investigation.events.findings[0]
        reasons.append(
            f"{len(investigation.events.findings)} failure event(s) correlated, "
            f"most frequent is {event.reason} on {event.object}."
        )

    if investigation.deployments.unhealthy_deployments:
        deployment = investigation.deployments.unhealthy_deployments[0]
        reasons.append(
            f"{len(investigation.deployments.unhealthy_deployments)} unhealthy deployment(s) "
            f"detected, including {deployment.namespace}/{deployment.name}."
        )

    if investigation.network.issues:
        issue = investigation.network.issues[0]
        reasons.append(
            f"{len(investigation.network.issues)} network issue(s) detected, "
            f"including {issue.kind} for {issue.namespace}/{issue.name}."
        )

    return reasons


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def _as_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()
