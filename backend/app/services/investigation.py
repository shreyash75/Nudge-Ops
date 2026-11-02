from collections.abc import Callable

from loguru import logger

from app.ai.agent import diagnose_cluster
from app.kubernetes.deployments import inspect_deployments
from app.kubernetes.errors import friendly_kubectl_error
from app.kubernetes.events import analyze_events
from app.kubernetes.logs import collect_logs
from app.kubernetes.network import inspect_network
from app.kubernetes.pods import inspect_pods
from app.models.schemas import (
    DeploymentsInvestigation,
    EventsInvestigation,
    InvestigateResponse,
    InvestigationPayload,
    LogsInvestigation,
    NetworkInvestigation,
    PodsInvestigation,
)


ProgressCallback = Callable[[str, str, str], None]

HEALTHY_CLUSTER_MESSAGE = "No critical Kubernetes issues detected. Cluster appears healthy."
AI_UNAVAILABLE_MESSAGE = (
    "AI diagnosis is temporarily unavailable. Kubernetes evidence was collected successfully."
)


def investigate_cluster(
    cluster: str | None = None,
    progress_callback: ProgressCallback | None = None,
) -> InvestigateResponse:
    """Collect Kubernetes troubleshooting evidence and request an AI diagnosis."""

    logger.info("Starting Kubernetes investigation for cluster {}", cluster or "current context")
    _notify(progress_callback, "starting", "running", "Starting investigation")

    try:
        _notify(progress_callback, "pods", "running", "Inspecting pod health")
        pods = inspect_pods(context=cluster)
        _notify(progress_callback, "pods", "completed", "Pod health checked")

        _notify(progress_callback, "logs", "running", "Collecting pod logs")
        logs = collect_logs(pods.problematic_pods, context=cluster)
        _notify(progress_callback, "logs", "completed", "Pod logs collected")

        _notify(progress_callback, "events", "running", "Analyzing cluster events")
        events = analyze_events(context=cluster)
        _notify(progress_callback, "events", "completed", "Cluster events analyzed")

        _notify(
            progress_callback,
            "deployments",
            "running",
            "Inspecting deployment health",
        )
        deployments = inspect_deployments(context=cluster)
        _notify(
            progress_callback,
            "deployments",
            "completed",
            "Deployment health checked",
        )

        _notify(progress_callback, "network", "running", "Inspecting network health")
        network = inspect_network(context=cluster)
        _notify(progress_callback, "network", "completed", "Network health checked")
    except Exception as exc:
        logger.exception("Investigation failed unexpectedly")
        message = friendly_kubectl_error(str(exc))
        _notify(progress_callback, "completed", "error", "Investigation failed")
        return InvestigateResponse(
            cluster=cluster,
            cluster_healthy=False,
            status="error",
            message=message,
            investigation=_empty_investigation(message),
        )

    errors = _friendly_errors(pods, events, deployments, network)
    if logs.error:
        errors.append(
            "Some pod logs could not be read. The diagnosis used the available evidence."
        )
    all_failed = _all_sections_failed(pods, events, deployments, network)
    status = "error" if all_failed else "success"
    has_issues = _has_issues(pods, events, deployments, network)
    cluster_healthy = status == "success" and not errors and not has_issues

    investigation = InvestigationPayload(
        pods=pods,
        logs=logs,
        events=events,
        deployments=deployments,
        network=network,
    )

    diagnosis = None
    message = "; ".join(errors) if errors else None

    if cluster_healthy:
        message = HEALTHY_CLUSTER_MESSAGE
        _notify(progress_callback, "diagnosis", "running", "Checking cluster health")
        _notify(progress_callback, "diagnosis", "completed", "No issues detected")
    elif status == "success" and has_issues:
        _notify(
            progress_callback,
            "diagnosis",
            "running",
            "Generating AI diagnosis",
        )
        diagnosis = diagnose_cluster(investigation)
        if diagnosis is not None:
            _notify(
                progress_callback,
                "diagnosis",
                "completed",
                "Root cause identified",
            )
        else:
            message = _merge_messages(message, AI_UNAVAILABLE_MESSAGE)
            _notify(
                progress_callback,
                "diagnosis",
                "error",
                "AI diagnosis unavailable",
            )
    elif status == "success":
        _notify(
            progress_callback,
            "diagnosis",
            "completed",
            "AI diagnosis skipped because evidence collection was incomplete",
        )
    else:
        _notify(progress_callback, "completed", "error", "Investigation failed")

    if status == "success":
        _notify(progress_callback, "completed", "completed", "Investigation complete")

    logger.info(
        "Kubernetes investigation finished for cluster {} with status {}",
        cluster or "current context",
        status,
    )
    return InvestigateResponse(
        cluster=cluster,
        cluster_healthy=cluster_healthy,
        status=status,
        message=message,
        investigation=investigation,
        diagnosis=diagnosis,
    )


def _notify(
    progress_callback: ProgressCallback | None,
    stage: str,
    status: str,
    message: str,
) -> None:
    if progress_callback is None:
        return

    try:
        progress_callback(stage, status, message)
    except Exception:
        logger.exception("Investigation progress callback failed")


def _friendly_errors(*sections: object) -> list[str]:
    messages: list[str] = []
    for section in sections:
        error = getattr(section, "error", None)
        if not error:
            continue

        friendly = friendly_kubectl_error(error)
        setattr(section, "error", friendly)
        if friendly not in messages:
            messages.append(friendly)

    return messages


def _merge_messages(current: str | None, extra: str) -> str:
    if not current:
        return extra
    if extra in current:
        return current
    return f"{current}\n\n{extra}"


def _has_issues(
    pods: PodsInvestigation,
    events: EventsInvestigation,
    deployments: DeploymentsInvestigation,
    network: NetworkInvestigation,
) -> bool:
    return bool(
        pods.problematic_pods
        or events.findings
        or deployments.unhealthy_deployments
        or network.issues
    )


def _all_sections_failed(
    pods: PodsInvestigation,
    events: EventsInvestigation,
    deployments: DeploymentsInvestigation,
    network: NetworkInvestigation,
) -> bool:
    return all(section.error for section in (pods, events, deployments, network))


def _empty_investigation(error: str) -> InvestigationPayload:
    return InvestigationPayload(
        pods=PodsInvestigation(healthy=False, error=error),
        logs=LogsInvestigation(error=error),
        events=EventsInvestigation(healthy=False, error=error),
        deployments=DeploymentsInvestigation(healthy=False, error=error),
        network=NetworkInvestigation(healthy=False, error=error),
    )
