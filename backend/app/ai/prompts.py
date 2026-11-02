import json

from app.models.schemas import InvestigationPayload

SYSTEM_PROMPT = """You are a Senior Kubernetes Site Reliability Engineer.

Diagnose the cluster incident using only the evidence provided. Correlate pod status, logs,
events, deployment health, and networking findings instead of summarizing each section alone.

Rules:
- Identify the most likely root cause that explains the correlated evidence.
- Set namespace to the affected namespace from the evidence, or null if the issue is cluster-wide.
- Do not invent resources, namespaces, errors, or evidence that is not present.
- If evidence is incomplete or conflicting, say so in the explanation and lower confidence.
- Prefer practical, beginner-friendly, Kubernetes-specific fixes.
- kubectl commands must be specific and safe to review before running.
- Confidence must be an integer from 0 to 100 based on evidence strength.

Return ONLY a single JSON object with exactly these keys:
{
  "root_cause": "concise root cause",
  "namespace": "affected namespace or null",
  "explanation": "clear explanation connecting the evidence",
  "fix": "actionable fix written for a beginner",
  "kubectl_commands": ["specific kubectl command", "another command if needed"],
  "prevention": "how to prevent this incident in the future",
  "confidence": 0,
  "confidence_reasoning": ["evidence-based reason for the score"]
}

Do not wrap the JSON in Markdown fences. Do not include any text outside the JSON object."""


def build_messages(investigation: InvestigationPayload) -> list[dict[str, str]]:
    """Build deterministic OpenRouter chat messages for the investigation."""

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": _build_user_prompt(investigation)},
    ]


def _build_user_prompt(investigation: InvestigationPayload) -> str:
    sections = [
        ("Pod Status", investigation.pods.model_dump()),
        ("Logs", investigation.logs.model_dump()),
        ("Events", investigation.events.model_dump()),
        ("Deployment Health", investigation.deployments.model_dump()),
        ("Networking Findings", investigation.network.model_dump()),
    ]

    rendered = "\n\n".join(
        f"## {title}\n{json.dumps(payload, indent=2, default=str)}"
        for title, payload in sections
    )

    return (
        "Analyze the following Kubernetes investigation evidence and return the incident "
        "diagnosis as JSON using the required schema.\n\n"
        f"{rendered}"
    )
