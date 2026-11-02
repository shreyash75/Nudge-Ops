from app.kubernetes.errors import friendly_kubectl_error


def test_missing_kubeconfig_message():
    message = friendly_kubectl_error(
        'error: config file "/root/.kube/config" not found'
    )
    assert "kubeconfig" in message.lower()
    assert "verify" in message.lower()


def test_cluster_unreachable_message():
    message = friendly_kubectl_error(
        "Unable to connect to the server: dial tcp 10.0.0.1:6443: i/o timeout"
    )
    assert "Unable to connect" in message
    assert "kubeconfig path" in message
    assert "cluster access" in message


def test_timeout_message():
    message = friendly_kubectl_error("kubectl timed out after 45 seconds")
    assert "timed out" in message.lower()


def test_kubectl_not_found_message():
    message = friendly_kubectl_error("kubectl was not found on PATH")
    assert "kubectl" in message
    assert "install" in message.lower()


def test_auth_denied_message():
    message = friendly_kubectl_error(
        "error: exec plugin: getting credentials: Unauthorized"
    )
    assert "denied" in message.lower()
    assert "credentials" in message.lower()


def test_context_missing_message():
    message = friendly_kubectl_error('context "gone" does not exist')
    assert "no longer available" in message


def test_empty_and_unknown_errors_are_never_reported_as_healthy():
    empty = friendly_kubectl_error("")
    unknown = friendly_kubectl_error("something exotic went wrong")
    assert "investigation failed" in empty.lower()
    assert "verify cluster access" in unknown.lower()
