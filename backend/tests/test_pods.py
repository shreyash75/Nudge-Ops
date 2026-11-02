from datetime import datetime, timedelta, timezone

from app.kubernetes.pods import _classify_pod


def _pod(
    *,
    container_statuses: list | None = None,
    phase: str = "Running",
    age_seconds: int = 600,
    conditions: list | None = None,
) -> dict:
    created_at = datetime.now(timezone.utc) - timedelta(seconds=age_seconds)
    return {
        "metadata": {
            "name": "my-app",
            "namespace": "demo",
            "creationTimestamp": created_at.isoformat().replace("+00:00", "Z"),
        },
        "status": {
            "phase": phase,
            "containerStatuses": container_statuses or [],
            "conditions": conditions or [],
        },
    }


def _waiting(reason: str, message: str) -> dict:
    return {
        "name": "app",
        "state": {"waiting": {"reason": reason, "message": message}},
    }


def _last_terminated(reason: str, message: str, exit_code: int) -> dict:
    return {
        "name": "app",
        "state": {"running": {}},
        "lastState": {
            "terminated": {
                "reason": reason,
                "message": message,
                "exitCode": exit_code,
                "finishedAt": "2026-01-01T00:00:00Z",
            }
        },
    }


def test_crashloopbackoff_is_detected():
    finding = _classify_pod(
        _pod(
            container_statuses=[
                _waiting("CrashLoopBackOff", "back-off restarting failed container")
            ]
        )
    )
    assert finding is not None
    assert finding.status == "CrashLoopBackOff"
    assert finding.namespace == "demo"
    assert finding.name == "my-app"


def test_imagepullbackoff_is_detected():
    finding = _classify_pod(
        _pod(
            container_statuses=[
                _waiting(
                    "ImagePullBackOff",
                    "Back-off pulling image registry.example.com/app:bad-tag",
                )
            ]
        )
    )
    assert finding is not None
    assert finding.status == "ImagePullBackOff"
    assert "bad-tag" in finding.message


def test_oomkilled_from_last_state_is_detected():
    finding = _classify_pod(
        _pod(
            container_statuses=[
                _last_terminated("OOMKilled", "Container exceeded memory limit", 137)
            ]
        )
    )
    assert finding is not None
    assert finding.status == "OOMKilled"
    assert "memory" in finding.message.lower()


def test_young_container_creating_pod_is_not_flagged():
    finding = _classify_pod(
        _pod(
            phase="Pending",
            age_seconds=30,
            container_statuses=[_waiting("ContainerCreating", "pulling image")],
        )
    )
    assert finding is None


def test_stuck_container_creating_pod_is_flagged():
    finding = _classify_pod(
        _pod(
            phase="Pending",
            age_seconds=400,
            container_statuses=[_waiting("ContainerCreating", "pulling image")],
        )
    )
    assert finding is not None
    assert finding.status == "ContainerCreating"


def test_stuck_pending_pod_is_flagged():
    conditions = [
        {"type": "PodScheduled", "status": "False", "message": "0/3 nodes available"}
    ]
    finding = _classify_pod(_pod(phase="Pending", age_seconds=300, conditions=conditions))
    assert finding is not None
    assert finding.status == "Pending"
    assert "nodes available" in finding.message


def test_failed_phase_pod_is_flagged():
    finding = _classify_pod(_pod(phase="Failed"))
    assert finding is not None
    assert finding.status == "Error"


def test_healthy_running_pod_is_not_flagged():
    finding = _classify_pod(
        _pod(
            container_statuses=[
                {"name": "app", "state": {"running": {"startedAt": "2026-01-01T00:00:00Z"}}}
            ]
        )
    )
    assert finding is None
