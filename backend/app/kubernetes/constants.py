POD_PROBLEM_REASONS = {
    "CrashLoopBackOff",
    "ImagePullBackOff",
    "ErrImagePull",
    "Error",
    "OOMKilled",
    "CreateContainerConfigError",
    "InvalidImageName",
    "RunContainerError",
}

EVENT_PROBLEM_REASONS = {
    "FailedScheduling",
    "BackOff",
    "FailedMount",
    "FailedPull",
    "ErrImagePull",
    "Unhealthy",
}

LOG_KEYWORDS = (
    "exception",
    "traceback",
    "error",
    "fatal",
    "panic",
    "connection refused",
    "connection reset",
    "i/o timeout",
    "timed out",
    "no such host",
    "unknown host",
    "dial tcp",
    "missing",
    "required",
    "environment variable",
    "env var",
    "imagepullbackoff",
    "errimagepull",
    "manifest unknown",
    "failed to pull",
    "failed to start",
    "crashloop",
    "oomkilled",
    "permission denied",
)

PENDING_STUCK_SECONDS = 60
CONTAINER_CREATING_STUCK_SECONDS = 120
KUBECTL_TIMEOUT_SECONDS = 45
LOG_TAIL_LINES = 100
MAX_LOG_HIGHLIGHTS = 40
MAX_PODS_TO_LOG = 10
MAX_EVENT_FINDINGS = 50
