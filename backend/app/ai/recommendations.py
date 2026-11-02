from typing import Any

from app.ai.analyzer import LLMResponseError


def build_recommendations(data: dict[str, Any]) -> tuple[str, list[str], str]:
    """Build the fix, kubectl commands, and prevention guidance from the diagnosis."""

    fix = _as_text(data.get("fix"))
    if not fix:
        raise LLMResponseError("LLM response is missing fix")

    commands = _extract_commands(data)
    prevention = _as_text(data.get("prevention"))

    return fix, commands, prevention


def _extract_commands(data: dict[str, Any]) -> list[str]:
    raw_commands = data.get("kubectl_commands")
    candidates: list[Any] = []

    if isinstance(raw_commands, list):
        candidates.extend(raw_commands)
    elif isinstance(raw_commands, str):
        candidates.append(raw_commands)

    singular = data.get("kubectl_command")
    if isinstance(singular, str):
        candidates.append(singular)

    commands: list[str] = []
    seen: set[str] = set()

    for candidate in candidates:
        command = _as_text(candidate)
        if not command:
            continue
        if command.startswith("$ "):
            command = command[2:].strip()
        if command in seen:
            continue
        seen.add(command)
        commands.append(command)

    return commands


def _as_text(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()
