from typing import Any

from loguru import logger

from app.kubernetes.executor import run_kubectl_json
from app.models.schemas import DeploymentsInvestigation, UnhealthyDeployment


def inspect_deployments(context: str | None = None) -> DeploymentsInvestigation:
    """Inspect deployments for replica and rollout problems."""

    payload, result = run_kubectl_json(["get", "deployments", "-A"], context=context)
    if payload is None:
        return DeploymentsInvestigation(
            healthy=False,
            unhealthy_deployments=[],
            error=result.error,
        )

    unhealthy: list[UnhealthyDeployment] = []
    for deployment in payload.get("items") or []:
        finding = _classify_deployment(deployment)
        if finding is not None:
            unhealthy.append(finding)

    logger.info("Deployment inspector found {} unhealthy deployments", len(unhealthy))
    return DeploymentsInvestigation(healthy=len(unhealthy) == 0, unhealthy_deployments=unhealthy)


def _classify_deployment(deployment: dict[str, Any]) -> UnhealthyDeployment | None:
    metadata = deployment.get("metadata") or {}
    spec = deployment.get("spec") or {}
    status = deployment.get("status") or {}
    conditions = status.get("conditions") or []

    replicas = int(spec.get("replicas") or 0)
    available = int(status.get("availableReplicas") or 0)
    unavailable = int(status.get("unavailableReplicas") or 0)
    condition_summaries, rollout_failed, available_false = _condition_summary(conditions)

    is_unhealthy = unavailable > 0 or available < replicas or rollout_failed or available_false
    if not is_unhealthy:
        return None

    return UnhealthyDeployment(
        name=metadata.get("name") or "unknown",
        namespace=metadata.get("namespace") or "default",
        replicas=replicas,
        available_replicas=available,
        unavailable_replicas=unavailable,
        conditions=condition_summaries,
        rollout_failed=rollout_failed,
    )


def _condition_summary(conditions: list[dict[str, Any]]) -> tuple[list[str], bool, bool]:
    summaries: list[str] = []
    rollout_failed = False
    available_false = False

    for condition in conditions:
        cond_type = condition.get("type") or "Unknown"
        cond_status = condition.get("status") or "Unknown"
        reason = condition.get("reason") or ""
        message = condition.get("message") or ""
        summaries.append(f"{cond_type}={cond_status} ({reason}): {message}".strip())

        if cond_type == "Progressing" and reason == "ProgressDeadlineExceeded":
            rollout_failed = True
        if cond_type == "Available" and cond_status == "False":
            available_false = True

    return summaries, rollout_failed, available_false
