def friendly_kubectl_error(message: str | None) -> str:
    """Translate raw kubectl failures into actionable, beginner-friendly messages."""

    text = (message or "").strip().lower()

    if not text:
        return (
            "Kubernetes investigation failed. Please verify cluster access and try again."
        )

    if "kubectl was not found" in text:
        return "kubectl is not installed or is not on PATH. Install kubectl and restart the backend."

    if "timed out after" in text or "request timed out" in text:
        return (
            "The Kubernetes request timed out. The cluster may be slow or unreachable.\n\n"
            "Please try again, or verify cluster access."
        )

    if (
        "no configuration has been provided" in text
        or "current-context is not set" in text
        or ("config file" in text and "not found" in text)
        or ("no such file" in text and "kube" in text)
    ):
        return (
            "Unable to load the Kubernetes kubeconfig.\n\n"
            "Please verify:\n"
            "- the kubeconfig path\n"
            "- that the file exists\n"
            "- that it contains at least one cluster"
        )

    if "context" in text and ("does not exist" in text or "not found" in text):
        return (
            "The selected Kubernetes cluster is no longer available in the kubeconfig. "
            "Refresh the cluster list and try again."
        )

    if any(
        marker in text
        for marker in (
            "unable to connect to the server",
            "connection refused",
            "i/o timeout",
            "no such host",
            "dial tcp",
            "getaddrinfo",
            "tls handshake",
            "x509",
            "context deadline exceeded",
            "network is unreachable",
        )
    ):
        return (
            "Unable to connect to the Kubernetes cluster.\n\n"
            "Please verify:\n"
            "- kubeconfig path\n"
            "- cluster access\n"
            "- kubectl permissions"
        )

    if any(
        marker in text
        for marker in (
            "unauthorized",
            "forbidden",
            "exec plugin",
            "getting credentials",
            "accessdenied",
            "access denied",
            "expired token",
            "invalid token",
            "must be logged in",
        )
    ):
        return (
            "Kubernetes access was denied.\n\n"
            "Please verify:\n"
            "- your cloud credentials\n"
            "- the kubeconfig authentication settings\n"
            "- your Kubernetes RBAC permissions"
        )

    return "Kubernetes investigation failed. Please verify cluster access and try again."
