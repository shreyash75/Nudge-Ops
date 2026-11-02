from typing import Any

from loguru import logger

from app.kubernetes.constants import (
    CONTAINER_CREATING_STUCK_SECONDS,
    PENDING_STUCK_SECONDS,
    POD_PROBLEM_REASONS,
)
from app.kubernetes.executor import run_kubectl_json
from app.kubernetes.time_utils import age_seconds
from app.models.schemas import PodsInvestigation, ProblematicPod


def inspect_pods(context: str | None = None) -> PodsInvestigation:
    """Collect pod status and detect unhealthy pods."""

    payload, result = run_kubectl_json(["get", "pods", "-A"], context=context)
    if payload is None:
        return PodsInvestigation(
            healthy=False,
            problematic_pods=[],
            total_pods=0,
            error=result.error,
        )

    items = payload.get("items") or []
    problematic: list[ProblematicPod] = []

    for pod in items:
        finding = _classify_pod(pod)
        if finding is not None:
            problematic.append(finding)

    logger.info("Pod inspector found {} problematic pods out of {}", len(problematic), len(items))
    return PodsInvestigation(
        healthy=len(problematic) == 0,
        problematic_pods=problematic,
        total_pods=len(items),
    )


def _classify_pod(pod: dict[str, Any]) -> ProblematicPod | None:
    metadata = pod.get("metadata") or {}
    status = pod.get("status") or {}
    name = metadata.get("name") or "unknown"
    namespace = metadata.get("namespace") or "default"
    phase = status.get("phase") or "Unknown"
    pod_age = age_seconds(metadata.get("creationTimestamp"))

    container_statuses = (status.get("containerStatuses") or []) + (status.get("initContainerStatuses") or [])
    detected_reason, message = _container_problem(container_statuses)

    if detected_reason is None:
        detected_reason, message = _phase_problem(phase, container_statuses, pod_age, status.get("conditions") or [])

    if detected_reason is None:
        return None

    return ProblematicPod(
        name=name,
        namespace=namespace,
        status=detected_reason,
        message=message,
        age_seconds=pod_age,
    )


def _container_problem(container_statuses: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    for container in container_statuses:
        waiting = (container.get("state") or {}).get("waiting") or {}
        terminated = (container.get("state") or {}).get("terminated") or {}
        last_terminated = (container.get("lastState") or {}).get("terminated") or {}

        for state in (waiting, terminated, last_terminated):
            reason = state.get("reason") or ""
            if reason == "OOMKilled" or reason in POD_PROBLEM_REASONS:
                return reason, state.get("message")

    return None, None


def _phase_problem(
    phase: str,
    container_statuses: list[dict[str, Any]],
    pod_age: int | None,
    conditions: list[dict[str, Any]],
) -> tuple[str | None, str | None]:
    waiting_reasons = []
    waiting_messages = []
    for container in container_statuses:
        waiting = (container.get("state") or {}).get("waiting") or {}
        if waiting.get("reason"):
            waiting_reasons.append(waiting["reason"])
            waiting_messages.append(waiting.get("message") or "")

    if "ContainerCreating" in waiting_reasons:
        if pod_age is not None and pod_age >= CONTAINER_CREATING_STUCK_SECONDS:
            return "ContainerCreating", waiting_messages[0] if waiting_messages else "Pod stuck in ContainerCreating"
        return None, None

    if phase == "Pending":
        if pod_age is not None and pod_age >= PENDING_STUCK_SECONDS:
            condition_message = _pending_message(conditions)
            return "Pending", condition_message or (waiting_messages[0] if waiting_messages else "Pod stuck in Pending")
        return None, None

    if phase == "Failed":
        return "Error", _pending_message(conditions) or "Pod phase is Failed"
    if phase == "Unknown":
        return "Error", "Pod phase is Unknown"

    return None, None


def _pending_message(conditions: list[dict[str, Any]]) -> str | None:
    for condition in conditions:
        if condition.get("status") == "False" and condition.get("message"):
            return str(condition["message"])
    return None
