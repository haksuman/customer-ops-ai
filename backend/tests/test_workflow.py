from unittest.mock import MagicMock, patch

import pytest

from app.graph.workflow import build_workflow
from app.models.schemas import Intent
from app.services.extractor import ExtractionResult


def _mock_extraction(intents, **entities):
    """Return a mock ExtractionResult with given intents and entities."""
    return ExtractionResult(intents=intents, **entities)


def run_graph(message: str, existing: dict | None = None, mock_extract=None, mock_llm_reply="ok") -> dict:
    state = existing or {
        "latest_message": "",
        "detected_intents": [],
        "pending_protected_intents": [],
        "entities": {},
        "auth_verified": False,
        "auth_missing_fields": [],
        "response_parts": [],
        "workflow_steps": [],
        "errors": [],
        "final_response": "",
        "handled_intents": [],
    }
    state["latest_message"] = message

    fake_llm_response = MagicMock()
    fake_llm_response.content = mock_llm_reply

    with (
        patch("app.services.extractor.extract", return_value=mock_extract),
        patch("app.graph.nodes.get_llm") as mock_get_llm,
    ):
        mock_get_llm.return_value.invoke.return_value = fake_llm_response
        graph = build_workflow()
        return graph.invoke(state)


def test_mixed_intent_missing_auth_still_returns_product_info():
    extraction = _mock_extraction(
        intents=[Intent.METER_READING_SUBMISSION, Intent.PRODUCT_INFO_REQUEST],
        meter_reading_kwh=1438,
        full_name="Julia Meyer",
    )
    result = run_graph(
        "Hello, I'd like to submit a meter reading of 1438 kWh and ask about dynamic tariff.",
        mock_extract=extraction,
        mock_llm_reply="Hello,\n\nHere is dynamic tariff info.\n\nKind regards,\nAI Service Assistant",
    )
    assert Intent.METER_READING_SUBMISSION in result["detected_intents"]
    assert Intent.PRODUCT_INFO_REQUEST in result["detected_intents"]
    assert result["auth_verified"] is False
    assert "dynamic tariff" in result["final_response"].lower()


def test_authenticated_follow_up_processes_protected_intent():
    first_extraction = _mock_extraction(
        intents=[Intent.METER_READING_SUBMISSION],
        meter_reading_kwh=1438,
    )
    first = run_graph(
        "Please submit my meter reading 1438 kWh.",
        mock_extract=first_extraction,
        mock_llm_reply="Hello,\n\nPlease provide auth.\n\nKind regards,\nAI Service Assistant",
    )
    assert first["pending_protected_intents"]
    assert first["auth_verified"] is False

    second_extraction = _mock_extraction(
        intents=[],
        contract_number="LB-123456",
        full_name="Julia Meyer",
        postal_code="20097",
    )
    second = run_graph(
        "Contract number LB-123456, Julia Meyer, postal code 20097.",
        existing=first,
        mock_extract=second_extraction,
        mock_llm_reply="Hello,\n\nYour meter reading has been recorded successfully.\n\nKind regards,\nAI Service Assistant",
    )
    assert second["auth_verified"] is True
    assert second["pending_protected_intents"] == []
    assert "recorded" in second["final_response"].lower()


def test_meter_anomaly_branch():
    extraction = _mock_extraction(
        intents=[Intent.METER_READING_SUBMISSION],
        contract_number="LB-123456",
        full_name="Julia Meyer",
        postal_code="20097",
        meter_reading_kwh=3000,
    )
    result = run_graph(
        "Please process meter reading 3000 kWh. Contract LB-123456, Julia Meyer, 20097.",
        mock_extract=extraction,
        mock_llm_reply="Hello,\n\nYour submitted reading looks unusually high.\n\nKind regards,\nAI Service Assistant",
    )
    assert result["auth_verified"] is True
    assert "unusually high" in result["final_response"].lower()
