import pytest

from app.ai.analyzer import (
    LLMResponseError,
    analyze_namespace,
    analyze_root_cause,
    parse_llm_response,
)
from app.models.schemas import (
    DeploymentsInvestigation,
    EventsInvestigation,
    InvestigationPayload,
    LogsInvestigation,
    NetworkInvestigation,
    PodsInvestigation,
)


def _empty_payload() -> InvestigationPayload:
    return InvestigationPayload(
        pods=PodsInvestigation(healthy=True),
        logs=LogsInvestigation(),
        events=EventsInvestigation(healthy=True),
        deployments=DeploymentsInvestigation(healthy=True),
        network=NetworkInvestigation(healthy=True),
    )


def test_parse_accepts_code_fenced_json():
    content = '```json\n{"root_cause": "bad image", "confidence": 80}\n```'
    data = parse_llm_response(content)
    assert data["root_cause"] == "bad image"


def test_parse_extracts_json_from_prose():
    content = 'Here you go: {"root_cause": "x", "confidence": 10} hope this helps'
    assert parse_llm_response(content)["root_cause"] == "x"


def test_parse_rejects_missing_json():
    with pytest.raises(LLMResponseError):
        parse_llm_response("no json here")


def test_root_cause_requires_fields():
    with pytest.raises(LLMResponseError):
        analyze_root_cause({"explanation": "only explanation"})
    root_cause, explanation = analyze_root_cause(
        {"root_cause": "OOMKilled", "explanation": "container hit memory limit"}
    )
    assert root_cause == "OOMKilled"
    assert "memory" in explanation


def test_namespace_falls_back_to_observed_namespaces():
    payload = _empty_payload()
    payload.pods.problematic_pods = [
        type("P", (), {"namespace": "payment", "name": "api"})()
    ]
    payload.logs.items = [type("L", (), {"namespace": "payment", "name": "api"})()]

    assert analyze_namespace({"namespace": "ALL"}, payload) == "payment"
    assert analyze_namespace({}, payload) == "payment"
    assert analyze_namespace({"namespace": "sre"}, payload) == "payment"
