from typing import Any

from loguru import logger

from app.kubernetes.executor import run_kubectl_json
from app.models.schemas import NetworkInvestigation, NetworkIssue


def inspect_network(context: str | None = None) -> NetworkInvestigation:
    """Inspect services, selectors, endpoints, and obvious DNS issues."""

    services_payload, services_result = run_kubectl_json(
        ["get", "svc", "-A"],
        context=context,
    )
    if services_payload is None:
        return NetworkInvestigation(healthy=False, issues=[], error=services_result.error)

    endpoints_payload, endpoints_result = run_kubectl_json(
        ["get", "endpoints", "-A"],
        context=context,
    )
    pods_payload, pods_result = run_kubectl_json(
        ["get", "pods", "-A"],
        context=context,
    )

    errors: list[str] = []
    if endpoints_payload is None and endpoints_result.error:
        errors.append(endpoints_result.error)
    if pods_payload is None and pods_result.error:
        errors.append(pods_result.error)
    endpoint_map = _index_by_namespace_name(endpoints_payload)
    pods = (pods_payload or {}).get("items") or []

    issues: list[NetworkIssue] = []
    dns_service_found = False

    for service in services_payload.get("items") or []:
        metadata = service.get("metadata") or {}
        spec = service.get("spec") or {}
        name = metadata.get("name") or "unknown"
        namespace = metadata.get("namespace") or "default"
        selector = spec.get("selector") or {}
        service_type = spec.get("type") or "ClusterIP"

        if name in {"kube-dns", "coredns"} and namespace == "kube-system":
            dns_service_found = True

        if service_type == "ExternalName":
            continue

        if selector:
            matching_pods = [pod for pod in pods if _pod_matches_selector(pod, namespace, selector)]
            if not matching_pods:
                issues.append(
                    NetworkIssue(
                        kind="selector_mismatch",
                        name=name,
                        namespace=namespace,
                        details=f"Service selector {selector} did not match any pods in {namespace}",
                    )
                )

        endpoint = endpoint_map.get((namespace, name))
        ready_addresses = _ready_address_count(endpoint)
        if ready_addresses == 0 and service_type != "ExternalName":
            issues.append(
                NetworkIssue(
                    kind="missing_endpoints",
                    name=name,
                    namespace=namespace,
                    details="Service has no ready endpoints",
                )
            )

    issues.extend(_dns_issues(dns_service_found, pods))

    unique_issues = _dedupe_issues(issues)
    logger.info("Network inspector found {} issues", len(unique_issues))
    error = "; ".join(errors) if errors else None
    return NetworkInvestigation(healthy=len(unique_issues) == 0, issues=unique_issues, error=error)


def _index_by_namespace_name(payload: dict[str, Any] | None) -> dict[tuple[str, str], dict[str, Any]]:
    indexed: dict[tuple[str, str], dict[str, Any]] = {}
    if not payload:
        return indexed
    for item in payload.get("items") or []:
        metadata = item.get("metadata") or {}
        indexed[(metadata.get("namespace") or "default", metadata.get("name") or "")] = item
    return indexed


def _pod_matches_selector(pod: dict[str, Any], namespace: str, selector: dict[str, str]) -> bool:
    metadata = pod.get("metadata") or {}
    if metadata.get("namespace") != namespace:
        return False
    labels = metadata.get("labels") or {}
    return all(labels.get(key) == value for key, value in selector.items())


def _ready_address_count(endpoint: dict[str, Any] | None) -> int:
    if not endpoint:
        return 0
    count = 0
    for subset in endpoint.get("subsets") or []:
        count += len(subset.get("addresses") or [])
    return count


def _dns_issues(dns_service_found: bool, pods: list[dict[str, Any]]) -> list[NetworkIssue]:
    issues: list[NetworkIssue] = []
    if not dns_service_found:
        issues.append(
            NetworkIssue(
                kind="dns",
                name="kube-dns/coredns",
                namespace="kube-system",
                details="Cluster DNS service (kube-dns or coredns) was not found in kube-system",
            )
        )

    dns_pods = [
        pod
        for pod in pods
        if (pod.get("metadata") or {}).get("namespace") == "kube-system"
        and "dns" in ((pod.get("metadata") or {}).get("name") or "").lower()
    ]
    unhealthy_dns = [
        pod
        for pod in dns_pods
        if (pod.get("status") or {}).get("phase") != "Running"
        or not _pod_ready(pod)
    ]
    for pod in unhealthy_dns:
        metadata = pod.get("metadata") or {}
        issues.append(
            NetworkIssue(
                kind="dns",
                name=metadata.get("name") or "dns-pod",
                namespace="kube-system",
                details=f"DNS pod phase is {(pod.get('status') or {}).get('phase') or 'Unknown'}",
            )
        )
    return issues


def _pod_ready(pod: dict[str, Any]) -> bool:
    for condition in (pod.get("status") or {}).get("conditions") or []:
        if condition.get("type") == "Ready":
            return condition.get("status") == "True"
    return False


def _dedupe_issues(issues: list[NetworkIssue]) -> list[NetworkIssue]:
    seen: set[tuple[str, str, str, str]] = set()
    unique: list[NetworkIssue] = []
    for issue in issues:
        key = (issue.kind, issue.namespace, issue.name, issue.details)
        if key in seen:
            continue
        seen.add(key)
        unique.append(issue)
    return unique
