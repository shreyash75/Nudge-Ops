import pytest

from app.models.schemas import (
    DeploymentsInvestigation,
    Diagnosis,
    EventFinding,
    EventsInvestigation,
    InvestigationPayload,
    LogsInvestigation,
    NetworkInvestigation,
    PodLogs,
    PodsInvestigation,
    ProblematicPod,
)
from app.services import investigation as investigation_service


def _payload(
    *,
    pods_error: str | None = None,
    events_error: str | None = None,
    deployments_error: str | None = None,
    network_error: str | None = None,
    logs_error: str | None = None,
    problems: list[ProblematicPod] | None = None,
) -> InvestigationPayload:
    pods = PodsInvestigation(
        healthy=pods_error is None,
        problematic_pods=problems or [],
        total_pods=0,
        error=pods_error,
    )
    logs = LogsInvestigation(
        items=[PodLogs(name="p", namespace="demo", highlights=[], truncated=False)],
        error=logs_error,
    )
    events = EventsInvestigation(
        healthy=(events_error is None and not problems),
        findings=[
            EventFinding(
                reason="BackOff", count=2, namespace="demo", object="Pod/p", message="m"
            )
        ]
        if problems and events_error is None
        else [],
        error=events_error,
    )
    deployments = DeploymentsInvestigation(
        healthy=deployments_error is None, error=deployments_error
    )
    network = NetworkInvestigation(healthy=network_error is None, error=network_error)
    return InvestigationPayload(
        pods=pods, logs=logs, events=events, deployments=deployments, network=network
    )


def _stub_collectors(
    monkeypatch,
    *,
    payload: InvestigationPayload,
    diagnose_result=None,
):
    diagnosis = (
        Diagnosis(root_cause="rc", explanation="e", fix="f", confidence=80)
        if diagnose_result == "diagnosed"
        else diagnose_result
    )
    monkeypatch.setattr(
        investigation_service,
        "inspect_pods",
        lambda context=None: payload.pods,
    )
    monkeypatch.setattr(
        investigation_service,
        "collect_logs",
        lambda problematic_pods, context=None: payload.logs,
    )
    monkeypatch.setattr(
        investigation_service,
        "analyze_events",
        lambda context=None: payload.events,
    )
    monkeypatch.setattr(
        investigation_service,
        "inspect_deployments",
        lambda context=None: payload.deployments,
    )
    monkeypatch.setattr(
        investigation_service,
        "inspect_network",
        lambda context=None: payload.network,
    )
    monkeypatch.setattr(
        investigation_service,
        "diagnose_cluster",
        lambda investigation: diagnosis,
    )


@pytest.fixture(autouse=True)
def no_openrouter(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("OPENROUTER_MODEL", raising=False)


def collect_events(callback):
    events = []
    return events, callback


def run(result_payload, monkeypatch, diagnose_status="diagnosed"):
    _stub_collectors(monkeypatch, payload=result_payload, diagnose_result=diagnose_status)
    events: list[tuple[str, str, str]] = []
    result = investigation_service.investigate_cluster(
        cluster="test",
        progress_callback=lambda stage, status, message: events.append((stage, status, message)),
    )
    return result, events


def test_full_failure_returns_error_and_is_never_healthy(monkeypatch):
    payload = _payload(
        pods_error="Unable to connect",
        events_error="Unable to connect",
        deployments_error="Unable to connect",
        network_error="Unable to connect",
    )
    result, events = run(payload, monkeypatch)

    assert result.status == "error"
    assert result.cluster_healthy is False
    assert result.diagnosis is None
    assert any(status == "error" for _, status, _ in events)


def test_partial_collection_failure_is_never_reported_healthy(monkeypatch):
    payload = _payload(events_error="Events API unavailable", pods_error="Pods unavailable")
    result, _ = run(payload, monkeypatch)

    assert result.status == "success"
    assert result.cluster_healthy is False
    assert result.diagnosis is None
    assert result.message  # a friendly error message is surfaced for the failed collectors


def test_log_read_failure_is_never_reported_healthy(monkeypatch):
    payload = _payload(logs_error="logs denied")
    result, _ = run(payload, monkeypatch)

    assert result.cluster_healthy is False
    assert "No critical Kubernetes issues" not in (result.message or "")
    assert "logs could not be read" in (result.message or "")


def test_healthy_cluster_message_when_all_evidence_is_available_and_clean(monkeypatch):
    payload = _payload()
    result, events = run(payload, monkeypatch)

    assert result.status == "success"
    assert result.cluster_healthy is True
    assert "No critical Kubernetes issues detected" in (result.message or "")
    assert any(stage == "completed" and status == "completed" for stage, status, _ in events)
    assert result.diagnosis is None


def test_problems_trigger_ai_diagnosis(monkeypatch):
    problems = [ProblematicPod(name="pod-0", namespace="demo", status="CrashLoopBackOff", message=None)]
    payload = _payload(problems=problems)
    result, events = run(payload, monkeypatch, diagnose_status="diagnosed")

    assert result.cluster_healthy is False
    assert result.diagnosis is not None
    assert any(stage == "diagnosis" and status == "completed" for stage, status, _ in events)


def test_ai_failure_keeps_cluster_not_healthy(monkeypatch):
    problems = [ProblematicPod(name="pod-0", namespace="demo", status="CrashLoopBackOff", message=None)]
    payload = _payload(problems=problems)
    _stub_collectors(monkeypatch, payload=payload, diagnose_result=None)
    result = investigation_service.investigate_cluster(cluster="test")

    assert result.status == "success"
    assert result.cluster_healthy is False
    assert result.diagnosis is None
    assert "temporarily unavailable" in (result.message or "")
