from app.kubernetes.events import analyze_events
from app.kubernetes.pods import inspect_pods

__all__ = ["inspect_pods", "inspect_nodes", "inspect_events"]


def inspect_nodes() -> None:
    """Placeholder: collect node status from the cluster."""
    pass


def inspect_events(context: str | None = None):
    """Collect cluster events for troubleshooting."""
    return analyze_events(context=context)
