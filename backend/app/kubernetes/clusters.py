from typing import Any

from loguru import logger

from app.kubernetes.errors import friendly_kubectl_error
from app.kubernetes.executor import run_kubectl, run_kubectl_json
from app.models.schemas import ClusterInfo, ClusterListResponse


def list_clusters() -> ClusterListResponse:
    """List every context available in the configured kubeconfig."""

    payload, result = run_kubectl_json(["config", "view"])
    if payload is None:
        return ClusterListResponse(
            clusters=[],
            current_context=None,
            error=friendly_kubectl_error(result.error),
        )

    cluster_servers = _cluster_servers(payload)
    current_context = payload.get("current-context") or None
    clusters = [
        _cluster_info(context, cluster_servers, current_context)
        for context in payload.get("contexts") or []
    ]
    clusters = [cluster for cluster in clusters if cluster is not None]
    clusters.sort(key=lambda cluster: (not cluster.is_current, cluster.name.lower()))

    logger.info("Found {} Kubernetes cluster contexts", len(clusters))
    return ClusterListResponse(
        clusters=clusters,
        current_context=current_context,
        error=None if clusters else "No Kubernetes clusters were found in the kubeconfig.",
    )


def current_context() -> str | None:
    """Return the active kubeconfig context, if one is configured."""

    result = run_kubectl(["config", "current-context"])
    if not result.success:
        return None

    context = result.stdout.strip()
    return context or None


def cluster_context_exists(context: str) -> tuple[bool, str | None]:
    """Check that a context from the request is still present in the kubeconfig."""

    result = run_kubectl(["config", "get-contexts", "-o", "name"])
    if not result.success:
        return False, friendly_kubectl_error(result.error)

    names = {name.strip() for name in result.stdout.splitlines() if name.strip()}
    if context not in names:
        return (
            False,
            "The selected Kubernetes cluster is no longer available in the kubeconfig. "
            "Refresh the cluster list and try again.",
        )

    return True, None


def _cluster_servers(payload: dict[str, Any]) -> dict[str, str]:
    servers: dict[str, str] = {}
    for cluster in payload.get("clusters") or []:
        name = cluster.get("name")
        server = (cluster.get("cluster") or {}).get("server")
        if name and server:
            servers[name] = server
    return servers


def _cluster_info(
    context: dict[str, Any],
    cluster_servers: dict[str, str],
    current_context: str | None,
) -> ClusterInfo | None:
    name = context.get("name")
    if not name:
        return None

    context_data = context.get("context") or {}
    cluster_name = context_data.get("cluster") or name

    return ClusterInfo(
        name=name,
        cluster=cluster_name,
        server=cluster_servers.get(cluster_name),
        namespace=context_data.get("namespace") or "default",
        is_current=name == current_context,
    )
