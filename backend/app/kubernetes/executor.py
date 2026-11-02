import json
import shutil
import subprocess
from typing import Any

from loguru import logger

from app.core.config import settings
from app.kubernetes.constants import KUBECTL_TIMEOUT_SECONDS
from app.models.schemas import KubectlResult


def run_kubectl(
    args: list[str],
    timeout: int = KUBECTL_TIMEOUT_SECONDS,
    context: str | None = None,
) -> KubectlResult:
    """Run a kubectl command and return structured stdout/stderr."""

    kubectl_bin = shutil.which("kubectl")
    if not kubectl_bin:
        logger.error("kubectl was not found on PATH")
        return KubectlResult(
            success=False,
            command=["kubectl", *args],
            stdout="",
            stderr="",
            exit_code=-1,
            error="kubectl was not found. Install kubectl and make sure it is on PATH.",
        )

    command = [kubectl_bin]
    kubeconfig = settings.kubeconfig_path.strip()
    if kubeconfig:
        command.extend(["--kubeconfig", kubeconfig])
    if context:
        command.extend(["--context", context])
    command.extend(args)

    logger.info("Running kubectl: {}", " ".join(command))

    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired:
        logger.error("kubectl timed out: {}", " ".join(command))
        return KubectlResult(
            success=False,
            command=command,
            stdout="",
            stderr="",
            exit_code=-1,
            error=f"kubectl timed out after {timeout} seconds",
        )
    except OSError as exc:
        logger.error("kubectl failed to start: {}", exc)
        return KubectlResult(
            success=False,
            command=command,
            stdout="",
            stderr="",
            exit_code=-1,
            error=str(exc),
        )

    stdout = completed.stdout.strip()
    stderr = completed.stderr.strip()
    success = completed.returncode == 0
    error = None if success else (stderr or f"kubectl exited with code {completed.returncode}")

    if success:
        logger.info("kubectl completed with exit code 0")
    else:
        logger.warning("kubectl failed with exit code {}: {}", completed.returncode, error)

    return KubectlResult(
        success=success,
        command=command,
        stdout=stdout,
        stderr=stderr,
        exit_code=completed.returncode,
        error=error,
    )


def run_kubectl_json(
    args: list[str],
    timeout: int = KUBECTL_TIMEOUT_SECONDS,
    context: str | None = None,
) -> tuple[Any | None, KubectlResult]:
    """Run kubectl with JSON output and parse the result."""

    result = run_kubectl([*args, "-o", "json"], timeout=timeout, context=context)
    if not result.success:
        return None, result

    try:
        return json.loads(result.stdout or "null"), result
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse kubectl JSON: {}", exc)
        return None, result.model_copy(update={"success": False, "error": "kubectl returned invalid JSON"})
