from app.kubernetes.network import _pod_matches_selector, _ready_address_count


def _pod(name: str, namespace: str, labels: dict) -> dict:
    return {"metadata": {"name": name, "namespace": namespace, "labels": labels}}


def test_selector_matching():
    pod = _pod("my-app", "demo", {"app": "my-app"})
    assert _pod_matches_selector(pod, "demo", {"app": "my-app"})
    assert not _pod_matches_selector(pod, "demo", {"app": "other"})
    assert not _pod_matches_selector(pod, "other-ns", {"app": "my-app"})


def test_ready_address_count():
    assert _ready_address_count(None) == 0
    endpoint = {"subsets": [{"addresses": [{"ip": "10.0.0.1"}, {"ip": "10.0.0.2"}]}]}
    assert _ready_address_count(endpoint) == 2
    empty = {"subsets": [{"notReadyAddresses": [{"ip": "10.0.0.3"}]}]}
    assert _ready_address_count(empty) == 0
