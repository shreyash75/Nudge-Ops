from app.kubernetes.deployments import _classify_deployment


def _deployment(
    *,
    replicas: int = 2,
    available: int = 2,
    unavailable: int = 0,
    conditions: list | None = None,
) -> dict:
    return {
        "metadata": {"name": "my-app", "namespace": "demo"},
        "spec": {"replicas": replicas},
        "status": {
            "availableReplicas": available,
            "unavailableReplicas": unavailable,
            "conditions": conditions
            or [{"type": "Available", "status": "True", "reason": ""}],
        },
    }


def test_unavailable_replicas_flagged():
    finding = _classify_deployment(_deployment(available=1))
    assert finding is not None
    assert finding.name == "my-app"
    assert finding.available_replicas == 1
    assert finding.unavailable_replicas == 0


def test_rollout_deadline_exceeded_flagged():
    conditions = [
        {
            "type": "Progressing",
            "status": "False",
            "reason": "ProgressDeadlineExceeded",
            "message": "Deployment exceeded its progress deadline",
        }
    ]
    finding = _classify_deployment(_deployment(conditions=conditions))
    assert finding is not None
    assert finding.rollout_failed is True
    assert any("Progressing=False" in summary for summary in finding.conditions)


def test_available_false_flagged():
    conditions = [{"type": "Available", "status": "False", "reason": "MinimumReplicasUnavailable"}]
    finding = _classify_deployment(_deployment(conditions=conditions))
    assert finding is not None


def test_healthy_deployment_not_flagged():
    finding = _classify_deployment(_deployment())
    assert finding is None
