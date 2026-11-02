"""Prompt 05: validate the AI agent against real Kubernetes failure scenarios.

Each test feeds the investigator's actual inspector classes with evidence shaped
like the kubectl output for a real cluster failure, then runs the full AI pipeline
(LLM response mocked) and asserts the diagnosis matches the expected root cause
and suggested fix for that scenario.
"""

import pytest

from app.ai import agent as agent_module
from app.kubernetes.deployments import _classify_deployment
from app.kubernetes.events import _summarize_events
from app.kubernetes.network import _pod_matches_selector
from app.kubernetes.pods import _classify_pod
from app.models.schemas import (
    DeploymentsInvestigation,
    Diagnosis,
    EventFinding,
    EventsInvestigation,
    InvestigationPayload,
    LogsInvestigation,
    NetworkInvestigation,
    NetworkIssue,
    PodLogs,
    PodsInvestigation,
    ProblematicPod,
    UnhealthyDeployment,
)
from app.services.investigation import investigate_cluster
from app.services import investigation as investigation_service


def _llm_response(scenario: str) -> dict:
    responses = {
        "crashloop": {
            "root_cause": "Missing required environment variable",
            "namespace": "demo",
            "explanation": "api-7d9f pod crash-loops: container exits immediately "
            "because the DB_PASSWORD environment variable is not set.",
            "fix": "Add the missing secret/configmap value to the deployment "
            "environment and redeploy.",
            "kubectl_commands": [
                "kubectl -n demo get deployment api -o yaml",
                "kubectl -n demo set env deployment/api DB_PASSWORD=***",
            ],
            "prevention": "Validate required env vars in CI before rollout.",
            "confidence": 90,
            "confidence_reasoning": [
                "CrashLoopBackOff on api-7d9f with an error log mentioning the missing env var."
            ],
        },
        "imagepull": {
            "root_cause": "Invalid image tag",
            "namespace": "demo",
            "explanation": "api-7d9f cannot start: the tag app:v999 does not exist "
            "in the registry, so ImagePullBackOff keeps retrying.",
            "fix": "Update the deployment image to a tag that exists in the registry.",
            "kubectl_commands": [
                "kubectl -n demo set image deployment/api app=registry.example.com/app:v1.2.3"
            ],
            "prevention": "Pin images to existing tags and verify them in CI.",
            "confidence": 95,
            "confidence_reasoning": ["ErrImagePull event mentions the unknown tag."],
        },
        "oom": {
            "root_cause": "Container exceeded its memory limit",
            "namespace": "demo",
            "explanation": "worker-0 was killed with OOMKilled (exit 137); usage "
            "exceeded the 128Mi limit defined on the container.",
            "fix": "Increase the memory requests/limits for the worker deployment.",
            "kubectl_commands": [
                "kubectl -n demo describe pod worker-0",
                "kubectl -n demo get deployment worker -o yaml",
            ],
            "prevention": "Load-test workloads and set memory limits with headroom.",
            "confidence": 90,
            "confidence_reasoning": ["OOMKilled termination reason on worker-0."],
        },
        "selector": {
            "root_cause": "Service selector does not match pod labels",
            "namespace": "demo",
            "explanation": "api-svc selects app=api-v1 but pods carry app=api-v2, "
            "so the service has zero endpoints and traffic is routed nowhere.",
            "fix": "Update the service selector to match the current pod labels.",
            "kubectl_commands": ["kubectl -n demo describe service api-svc"],
            "prevention": "Keep selectors in sync with deployment pod labels via CI checks.",
            "confidence": 85,
            "confidence_reasoning": ["Selector mismatch found while inspecting services."],
        },
    }
    return responses[scenario]


def _payload(
    *,
    pods: list[ProblematicPod],
    highlights: list[str],
    events: list[EventFinding],
    deployments: list[UnhealthyDeployment] | None = None,
    network: list[NetworkIssue] | None = None,
) -> InvestigationPayload:
    return InvestigationPayload(
        pods=PodsInvestigation(
            healthy=not pods, problematic_pods=pods, total_pods=3
        ),
        logs=LogsInvestigation(
            items=[PodLogs(name=pods[0].name, namespace=pods[0].namespace, highlights=highlights, truncated=False)]
            if pods
            else [],
        ),
        events=EventsInvestigation(healthy=not events, findings=events),
        deployments=DeploymentsInvestigation(
            healthy=not deployments, unhealthy_deployments=deployments or []
        ),
        network=NetworkInvestigation(healthy=not network, issues=network or []),
    )


def _stub_llm(monkeypatch, scenario: str):
    import json

    monkeypatch.setattr(agent_module.settings, "openrouter_api_key", "test-key", raising=False)
    monkeypatch.setattr(agent_module.settings, "openrouter_model", "test-model", raising=False)
    monkeypatch.setattr(
        agent_module,
        "request_completion",
        lambda messages: json.dumps(_llm_response(scenario)),
    )


def test_scenario_1_crashloopbackoff_missing_env_var(monkeypatch):
    pod = _classify_pod(
        {"metadata": {"name": "api-7d9f", "namespace": "demo"},
         "status": {"phase": "Running",
                    "containerStatuses": [
                        {"name": "app",
                         "state": {"waiting": {"reason": "CrashLoopBackOff", "message": "back-off restarting"}}}]}},
    )
    assert pod is not None and pod.status == "CrashLoopBackOff"

    payload = _payload(
        pods=[pod],
        highlights=["KeyError: 'DB_PASSWORD' is missing from environment variable DB_PASSWORD"],
        events=_summarize_events(
            [{"reason": "BackOff", "count": 6, "message": "Back-off restarting failed container",
              "involvedObject": {"kind": "Pod", "name": "api-7d9f", "namespace": "demo"},
              "lastTimestamp": "2026-01-01T00:00:00Z"}],
            5,
        ),
    )
    _stub_llm(monkeypatch, "crashloop")

    diagnosis = agent_module.diagnose_cluster(payload)
    assert isinstance(diagnosis, Diagnosis)
    assert diagnosis.namespace == "demo"
    assert "environment variable" in diagnosis.root_cause.lower()
    assert "secret" in diagnosis.fix.lower() or "configmap" in diagnosis.fix.lower()
    assert diagnosis.confidence >= 80
    assert any("kubectl" in command for command in diagnosis.kubectl_commands)


def test_scenario_2_imagepullbackoff_wrong_tag(monkeypatch):
    pod = _classify_pod(
        {"metadata": {"name": "api-7d9f", "namespace": "demo"},
         "status": {"phase": "Pending",
                    "containerStatuses": [
                        {"name": "app",
                         "state": {"waiting": {"reason": "ImagePullBackOff", "message": "Back-off pulling image app:v999"}}}]}},
    )
    assert pod is not None and pod.status == "ImagePullBackOff"

    payload = _payload(
        pods=[pod],
        highlights=["Failed to pull image registry.example.com/app:v999: manifest unknown"],
        events=_summarize_events(
            [{"reason": "ErrImagePull", "count": 4, "message": "pull access denied / manifest unknown: app:v999",
              "involvedObject": {"kind": "Pod", "name": "api-7d9f", "namespace": "demo"},
              "lastTimestamp": "2026-01-01T00:00:00Z"}],
            5,
        ),
    )
    _stub_llm(monkeypatch, "imagepull")

    diagnosis = agent_module.diagnose_cluster(payload)
    assert "image tag" in diagnosis.root_cause.lower()
    assert "set image" in diagnosis.fix.lower() or "update" in diagnosis.fix.lower()
    assert diagnosis.confidence >= 80


def test_scenario_3_oomkilled_low_memory_limit(monkeypatch):
    pod = _classify_pod(
        {"metadata": {"name": "worker-0", "namespace": "demo"},
         "status": {"phase": "Running",
                    "containerStatuses": [
                        {"name": "worker",
                         "state": {"running": {"startedAt": "2026-01-01T00:00:00Z"}},
                         "lastState": {"terminated": {"reason": "OOMKilled", "exitCode": 137,
                                                      "message": "Container used more memory than limit"}}}]}},
    )
    assert pod is not None and pod.status == "OOMKilled"

    payload = _payload(
        pods=[pod],
        highlights=["fatal error: out of memory", "signal: killed"],
        events=_summarize_events(
            [{"reason": "Unhealthy", "count": 2, "message": "readiness probe failed",
              "involvedObject": {"kind": "Pod", "name": "worker-0", "namespace": "demo"},
              "lastTimestamp": "2026-01-01T00:00:00Z"}],
            5,
        ),
    )
    _stub_llm(monkeypatch, "oom")

    diagnosis = agent_module.diagnose_cluster(payload)
    assert "memory" in diagnosis.root_cause.lower()
    assert "memory" in diagnosis.fix.lower()
    assert "requests/limits" in diagnosis.fix.lower() or "increase" in diagnosis.fix.lower()


def test_scenario_4_service_selector_mismatch(monkeypatch):
    selector = {"app": "api-v1"}
    pod_labels = {"app": "api-v2"}
    pod = {"metadata": {"name": "api-v2", "namespace": "demo", "labels": pod_labels}}
    assert not _pod_matches_selector(pod, "demo", selector)

    issue = NetworkIssue(
        kind="selector_mismatch",
        name="api-svc",
        namespace="demo",
        details=f"Service selector {selector} did not match any pods in demo",
    )
    payload = _payload(
        pods=[
            ProblematicPod(name="endpointless", namespace="demo", status="Error", message="service endpoints empty")
        ],
        highlights=[],
        events=[],
        network=[issue],
    )
    _stub_llm(monkeypatch, "selector")

    diagnosis = agent_module.diagnose_cluster(payload)
    assert "selector" in diagnosis.root_cause.lower()
    assert "selector" in diagnosis.fix.lower()


def test_scenario_rollout_failure_suggested_fix(monkeypatch):
    unhealthy = _classify_deployment(
        {"metadata": {"name": "api", "namespace": "demo"},
         "spec": {"replicas": 2},
         "status": {"availableReplicas": 0, "unavailableReplicas": 2,
                    "conditions": [{"type": "Progressing", "status": "False",
                                    "reason": "ProgressDeadlineExceeded",
                                    "message": "progress deadline exceeded"}]}},
    )
    assert unhealthy is not None and unhealthy.rollout_failed

    payload = _payload(
        pods=[ProblematicPod(name="api-rollout", namespace="demo", status="CrashLoopBackOff", message=None)],
        highlights=["error: image back-off pulling app:broken"],
        events=_summarize_events(
            [{"reason": "BackOff", "count": 8, "message": "Back-off pulling image app:broken",
              "involvedObject": {"kind": "Pod", "name": "api-rollout", "namespace": "demo"},
              "lastTimestamp": "2026-01-01T00:00:00Z"}],
            5,
        ),
        deployments=[unhealthy],
    )
    _stub_llm(monkeypatch, "imagepull")

    diagnosis = agent_module.diagnose_cluster(payload)
    assert diagnosis.confidence >= 80
    assert "image" in diagnosis.root_cause.lower()


def test_investigation_reports_scenarios_not_healthy(monkeypatch):
    """Evidence with pods/events problems must never be classified as healthy."""

    pod = ProblematicPod(name="api", namespace="demo", status="ImagePullBackOff", message="x")
    payload = _payload(
        pods=[pod],
        highlights=["manifest unknown"],
        events=[
            EventFinding(reason="ErrImagePull", count=3, namespace="demo", object="Pod/api", message="m")
        ],
    )
    for name in ("inspect_pods",):
        monkeypatch.setattr(investigation_service, name, lambda context=None: payload.pods)
    monkeypatch.setattr(
        investigation_service, "collect_logs", lambda problematic_pods, context=None: payload.logs
    )
    monkeypatch.setattr(
        investigation_service, "analyze_events", lambda context=None: payload.events
    )
    monkeypatch.setattr(
        investigation_service, "inspect_deployments", lambda context=None: payload.deployments
    )
    monkeypatch.setattr(
        investigation_service, "inspect_network", lambda context=None: payload.network
    )
    from app.ai import agent as agent_module

    monkeypatch.setattr(agent_module.settings, "openrouter_api_key", "", raising=False)

    result = investigate_cluster(cluster="test")
    assert result.cluster_healthy is False
    assert result.status == "success"
    assert result.diagnosis is None
