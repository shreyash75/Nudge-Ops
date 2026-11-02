from app.ai.confidence import _fallback_confidence, calculate_confidence
from app.models.schemas import (
    DeploymentsInvestigation,
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


def _payload(
    *,
    pods: int = 0,
    logs: int = 0,
    events: int = 0,
    deployments: int = 0,
    network: int = 0,
) -> InvestigationPayload:
    problematic = [
        ProblematicPod(
            name=f"pod-{index}", namespace="demo", status="CrashLoopBackOff", message=None
        )
        for index in range(pods)
    ]
    log_items = [
        PodLogs(name="pod-0", namespace="demo", highlights=["Traceback"], truncated=False)
    ] * logs
    findings = [
        EventFinding(
            reason="BackOff",
            count=3,
            namespace="demo",
            object="Pod/pod-0",
            message="x",
            last_seen=None,
        )
    ] * events
    unhealthy = [
        UnhealthyDeployment(
            name="api",
            namespace="demo",
            replicas=2,
            available_replicas=1,
            unavailable_replicas=1,
            conditions=[],
            rollout_failed=False,
        )
    ] * deployments
    issues = [
        NetworkIssue(
            kind="selector_mismatch", name="api", namespace="demo", details="no match"
        )
    ] * network

    return InvestigationPayload(
        pods=PodsInvestigation(
            healthy=pods == 0, problematic_pods=problematic, total_pods=pods
        ),
        logs=LogsInvestigation(items=log_items),
        events=EventsInvestigation(healthy=events == 0, findings=findings),
        deployments=DeploymentsInvestigation(healthy=deployments == 0, unhealthy_deployments=unhealthy),
        network=NetworkInvestigation(healthy=network == 0, issues=issues),
    )


def test_confidence_from_llm_is_normalised():
    confidence, reasoning = calculate_confidence(
        {"confidence": 120, "confidence_reasoning": ["strong logs"]},
        _payload(),
    )
    assert confidence == 100
    assert reasoning == ["strong logs"]


def test_confidence_extracted_from_text():
    confidence, _ = calculate_confidence({"confidence": "about 75 percent"}, _payload())
    assert confidence == 75


def test_fallback_confidence_scales_with_signals():
    assert _fallback_confidence(_payload(pods=1, logs=1, events=1)) == 85
    assert _fallback_confidence(_payload(pods=1, events=1)) == 75
    assert _fallback_confidence(_payload(pods=1)) == 65
    assert _fallback_confidence(_payload()) == 40


def test_reasoning_is_generated_from_evidence_when_missing():
    _, reasoning = calculate_confidence({}, _payload(pods=1, events=1))
    assert any("problematic pod" in reason.lower() for reason in reasoning)
