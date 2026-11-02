from loguru import logger

from app.kubernetes.constants import LOG_KEYWORDS, LOG_TAIL_LINES, MAX_LOG_HIGHLIGHTS, MAX_PODS_TO_LOG
from app.kubernetes.executor import run_kubectl
from app.models.schemas import LogsInvestigation, PodLogs, ProblematicPod


def collect_logs(
    problematic_pods: list[ProblematicPod],
    context: str | None = None,
) -> LogsInvestigation:
    """Fetch concise failure-focused logs for unhealthy pods."""

    items: list[PodLogs] = []
    errors: list[str] = []

    for pod in problematic_pods[:MAX_PODS_TO_LOG]:
        log_text, error = _read_pod_logs(pod, context)
        if error:
            errors.append(f"{pod.namespace}/{pod.name}: {error}")
        highlights, truncated = extract_highlights(log_text)
        items.append(
            PodLogs(
                name=pod.name,
                namespace=pod.namespace,
                highlights=highlights,
                truncated=truncated,
            )
        )

    logger.info("Logs collector captured logs for {} pods", len(items))
    return LogsInvestigation(items=items, error="; ".join(errors) if errors else None)


def _read_pod_logs(
    pod: ProblematicPod,
    context: str | None = None,
) -> tuple[str, str | None]:
    args = ["logs", pod.name, "-n", pod.namespace, "--all-containers=true", f"--tail={LOG_TAIL_LINES}"]
    result = run_kubectl(args, context=context)
    log_text = result.stdout

    if not log_text and pod.status in {"CrashLoopBackOff", "Error", "OOMKilled"}:
        previous = run_kubectl([*args, "--previous"], context=context)
        if previous.success and previous.stdout:
            log_text = previous.stdout
        elif not result.success:
            return "", result.error
        elif not previous.success:
            return log_text, previous.error

    if not result.success and not log_text:
        return "", result.error

    return log_text, None if result.success or log_text else result.error


def extract_highlights(log_text: str, max_lines: int = MAX_LOG_HIGHLIGHTS) -> tuple[list[str], bool]:
    lines = [line.strip() for line in log_text.splitlines() if line.strip()]
    matched = [line for line in lines if _is_relevant(line)]
    source = matched if matched else lines[-20:]
    truncated = len(source) > max_lines
    return source[-max_lines:], truncated


def _is_relevant(line: str) -> bool:
    lowered = line.lower()
    return any(keyword in lowered for keyword in LOG_KEYWORDS)
