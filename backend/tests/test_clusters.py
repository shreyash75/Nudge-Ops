from app.kubernetes.clusters import _cluster_info, _cluster_servers


def _kubeconfig_payload() -> dict:
    return {
        "current-context": "prod",
        "clusters": [
            {"name": "prod-cluster", "cluster": {"server": "https://prod.example.com"}},
            {"name": "sandbox-cluster", "cluster": {"server": "https://sandbox.example.com"}},
            {"name": "serverless", "cluster": {}},
        ],
        "contexts": [
            {
                "name": "prod",
                "context": {"cluster": "prod-cluster", "namespace": "app", "user": "ops"},
            },
            {
                "name": "sandbox",
                "context": {"cluster": "sandbox-cluster"},
            },
            {"name": "broken", "context": {}},
        ],
    }


def test_cluster_servers_indexed():
    servers = _cluster_servers(_kubeconfig_payload())
    assert servers == {
        "prod-cluster": "https://prod.example.com",
        "sandbox-cluster": "https://sandbox.example.com",
    }


def test_cluster_info_contains_server_and_namespace():
    payload = _kubeconfig_payload()
    info = _cluster_info(payload["contexts"][0], _cluster_servers(payload), "prod")
    assert info is not None
    assert info.name == "prod"
    assert info.server == "https://prod.example.com"
    assert info.namespace == "app"
    assert info.is_current is True


def test_context_without_cluster_yields_default_namespace():
    payload = _kubeconfig_payload()
    info = _cluster_info(payload["contexts"][1], _cluster_servers(payload), "prod")
    assert info is not None
    assert info.is_current is False
    assert info.namespace == "default"
