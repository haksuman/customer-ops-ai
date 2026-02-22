from app.graph.workflow import build_workflow
from app.models.schemas import Intent


def run_graph(message: str, existing: dict | None = None) -> dict:
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
    graph = build_workflow()
    return graph.invoke(state)


def test_mixed_intent_missing_auth_still_returns_product_info():
    result = run_graph(
        (
            "Hello, I'd like to submit a meter reading of 1438 kWh "
            "and ask about dynamic tariff options. Best, Julia Meyer"
        )
    )
    assert Intent.METER_READING_SUBMISSION in result["detected_intents"]
    assert Intent.PRODUCT_INFO_REQUEST in result["detected_intents"]
    assert result["auth_verified"] is False
    assert "dynamic tariff" in result["final_response"].lower()


def test_authenticated_follow_up_processes_protected_intent():
    first = run_graph("Please submit my meter reading 1438 kWh.")
    assert first["pending_protected_intents"]
    assert first["auth_verified"] is False

    second = run_graph(
        "Contract number LB-123456, Julia Meyer, postal code 20097.",
        existing=first,
    )
    assert second["auth_verified"] is True
    assert second["pending_protected_intents"] == []
    assert "recorded" in second["final_response"].lower()


def test_meter_anomaly_branch():
    result = run_graph(
        (
            "Please process meter reading 3000 kWh. "
            "Contract number LB-123456, Julia Meyer, postal code 20097."
        )
    )
    assert result["auth_verified"] is True
    assert "unusually high" in result["final_response"].lower()
