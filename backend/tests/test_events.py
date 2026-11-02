from app.kubernetes.events import _summarize_events


def _event(
    reason: str,
    name: str,
    namespace: str = "demo",
    kind: str = "Pod",
    count: int = 1,
    message: str = "something happened",
) -> dict:
    return {
        "reason": reason,
        "count": count,
        "message": message,
        "involvedObject": {"kind": kind, "name": name, "namespace": namespace},
        "lastTimestamp": "2026-01-01T00:00:00Z",
    }


def _summarize(items: list[dict], max_findings: int = 10):
    return _summarize_events(items, max_findings)


def test_problem_reasons_are_grouped_and_counted():
    findings = _summarize(
        [
            _event("BackOff", "my-app", count=5),
            _event("BackOff", "my-app", count=2),
            _event("Unhealthy", "my-app", kind="Deployment", message="probe failed"),
        ]
    )

    assert len(findings) == 2
    by_object = {finding.object: finding for finding in findings}
    assert by_object["Pod/my-app"].count == 7
    assert by_object["Deployment/my-app"].reason == "Unhealthy"


def test_informational_events_are_ignored():
    findings = _summarize([_event("Pulling", "my-app", message="Pulling image")])
    assert findings == []


def test_findings_are_capped():
    items = [_event("BackOff", f"pod-{index}", namespace=f"ns-{index}") for index in range(8)]
    findings = _summarize(items, max_findings=5)
    assert len(findings) == 5
