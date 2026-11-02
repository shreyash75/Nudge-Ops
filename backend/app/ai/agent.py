from loguru import logger

from app.ai.analyzer import (
    LLMResponseError,
    analyze_namespace,
    analyze_root_cause,
    parse_llm_response,
)
from app.ai.client import LLMClientError, request_completion
from app.ai.confidence import calculate_confidence
from app.ai.prompts import build_messages
from app.ai.recommendations import build_recommendations
from app.core.config import settings
from app.models.schemas import Diagnosis, InvestigationPayload


def diagnose_cluster(investigation: InvestigationPayload) -> Diagnosis | None:
    """Send investigation evidence to the LLM and build a structured diagnosis."""

    if not settings.openrouter_api_key.strip() or not settings.openrouter_model.strip():
        logger.warning("AI diagnosis skipped because OpenRouter is not configured")
        return None

    try:
        messages = build_messages(investigation)
        content = request_completion(messages)
        data = parse_llm_response(content)

        root_cause, explanation = analyze_root_cause(data)
        namespace = analyze_namespace(data, investigation)
        fix, commands, prevention = build_recommendations(data)
        confidence, reasoning = calculate_confidence(data, investigation)

        diagnosis = Diagnosis(
            root_cause=root_cause,
            namespace=namespace,
            explanation=explanation,
            fix=fix,
            kubectl_command=commands[0] if commands else None,
            kubectl_commands=commands,
            prevention=prevention,
            confidence=confidence,
            confidence_reasoning=reasoning,
        )

        logger.info("AI diagnosis completed with confidence {}%", confidence)
        return diagnosis

    except (LLMClientError, LLMResponseError) as exc:
        logger.error("AI diagnosis failed: {}", exc)
        return None
    except Exception:
        logger.exception("AI diagnosis failed unexpectedly")
        return None
