import json
from typing import Any

from app.models.schemas import InvestigationPayload


class LLMResponseError(Exception):
    """Raised when the LLM response does not match the expected diagnosis contract."""


_NAMESPACE_PLACEHOLDERS = {
    "",
    "all",
    "all namespaces",
    "cluster",
    "cluster wide",
    "cluster-wide",
    "n/a",
    "none",
    "null",
    "unknown",
}


def parse_llm_response(content: str) -> dict[str, Any]:
    """Extract and parse the JSON diagnosis object from the LLM response."""

    cleaned = _strip_code_fences(content)
    start = cleaned.find("{")
    end = cleaned.rfind("}")

    if start == -1 or end == -1 or end < start:
        raise LLMResponseError("LLM response did not contain a JSON object")

    try:
        parsed = json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMResponseError(f"LLM response contained invalid JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise LLMResponseError("LLM response JSON must be an object")

    return parsed


def analyze_root_cause(data: dict[str, Any]) -> tuple[str, str]:
    """Extract the root cause and correlated explanation from the diagnosis."""

    root_cause = _clean_text(data.get("root_cause"))
    explanation = _clean_text(data.get("explanation"))

    if not root_cause:
        raise LLMResponseError("LLM response is missing root_cause")
    if not explanation:
        raise LLMResponseError("LLM response is missing explanation")

    return root_cause, explanation


def analyze_namespace(
    data: dict[str, Any],
    investigation: InvestigationPayload,
) -> str | None:
    """Resolve the affected namespace from the diagnosis and observed evidence."""

    observed = _observed_namespaces(investigation)
    raw = _clean_text(data.get("namespace"))

    if raw and raw.lower() not in _NAMESPACE_PLACEHOLDERS:
        for namespace in observed:
            if namespace.lower() == raw.lower():
                return namespace

    return observed[0] if observed else None


def _observed_namespaces(investigation: InvestigationPayload) -> list[str]:
    namespaces: list[str] = []
    seen: set[str] = set()

    candidates = [
        *(pod.namespace for pod in investigation.pods.problematic_pods),
        *(item.namespace for item in investigation.logs.items),
        *(
            deployment.namespace
            for deployment in investigation.deployments.unhealthy_deployments
        ),
        *(issue.namespace for issue in investigation.network.issues),
        *(finding.namespace for finding in investigation.events.findings),
    ]

    for candidate in candidates:
        namespace = _clean_text(candidate)
        key = namespace.lower()
        if not namespace or key in _NAMESPACE_PLACEHOLDERS or key in seen:
            continue
        seen.add(key)
        namespaces.append(namespace)

    return namespaces


def _strip_code_fences(content: str) -> str:
    cleaned = content.strip()
    if not cleaned.startswith("```"):
        return cleaned

    lines = cleaned.splitlines()
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]

    return "\n".join(lines).strip()


def _clean_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()
