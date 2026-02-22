from __future__ import annotations

import logging
from typing import Any

from app.domain.auth_policy import get_missing_auth_fields, needs_auth, verify_auth
from app.models.schemas import AUTH_REQUIRED_INTENTS, Intent
from app.services.extractor import detect_intents, extract_entities
from app.services.mock_repos import MockCustomerRepository, MockProductRepository

logger = logging.getLogger(__name__)


def _append_step(state: dict[str, Any], name: str, status: str, detail: str) -> None:
    state["workflow_steps"].append({"name": name, "status": status, "detail": detail})


def extract_and_detect_node(state: dict[str, Any]) -> dict[str, Any]:
    step = "extract_and_detect"
    _append_step(state, step, "running", "Extracting entities and intents from latest email.")
    try:
        text = state["latest_message"]
        detected = detect_intents(text)
        extracted = extract_entities(text)

        state["detected_intents"] = detected
        state["entities"].update(extracted)

        logger.info(
            "node_completed",
            extra={
                "node": step,
                "detected_intents": [intent.value for intent in detected],
                "entity_keys": list(extracted.keys()),
            },
        )
        _append_step(state, step, "completed", f"Detected {len(detected)} intent(s).")
    except Exception as exc:  # pragma: no cover
        logger.exception("node_failed", extra={"node": step})
        state["errors"].append(str(exc))
        _append_step(state, step, "failed", str(exc))
    return state


def handle_no_auth_intents_node(state: dict[str, Any]) -> dict[str, Any]:
    step = "handle_no_auth_intents"
    _append_step(state, step, "running", "Handling intents that do not require authentication.")
    no_auth_intents = [intent for intent in state["detected_intents"] if intent not in AUTH_REQUIRED_INTENTS]
    if not no_auth_intents:
        _append_step(state, step, "skipped", "No public intents detected.")
        return state

    product_repo = MockProductRepository()
    for intent in no_auth_intents:
        if intent == Intent.PRODUCT_INFO_REQUEST:
            state["response_parts"].append(product_repo.get_dynamic_tariff_info())
            state.setdefault("handled_intents", []).append(intent)
        elif intent == Intent.GENERAL_FEEDBACK:
            state["response_parts"].append("Thank you for your feedback. We appreciate you reaching out.")
            state.setdefault("handled_intents", []).append(intent)

    _append_step(state, step, "completed", f"Handled {len(no_auth_intents)} no-auth intent(s).")
    return state


def auth_policy_node(state: dict[str, Any]) -> dict[str, Any]:
    step = "auth_policy"
    _append_step(state, step, "running", "Evaluating whether authentication is required.")

    protected_intents = [intent for intent in state["detected_intents"] if intent in AUTH_REQUIRED_INTENTS]
    pending = state.get("pending_protected_intents", [])
    if protected_intents:
        state["pending_protected_intents"] = list({*pending, *protected_intents})

    all_protected = state.get("pending_protected_intents", [])
    if not needs_auth(all_protected):
        _append_step(state, step, "completed", "No auth-required intent pending.")
        return state

    missing = get_missing_auth_fields(state["entities"])
    state["auth_missing_fields"] = missing
    if missing:
        state["auth_verified"] = False
        _append_step(state, step, "completed", f"Missing fields: {', '.join(missing)}.")
        return state

    repo = MockCustomerRepository()
    state["auth_verified"] = verify_auth(state["entities"], repo)
    if not state["auth_verified"]:
        state["errors"].append("Authentication failed with provided customer data.")
        _append_step(state, step, "completed", "Auth fields present but verification failed.")
    else:
        _append_step(state, step, "completed", "Authentication successful.")
    return state


def compose_auth_request_node(state: dict[str, Any]) -> dict[str, Any]:
    step = "compose_auth_request"
    _append_step(state, step, "running", "Composing follow-up for missing authentication data.")
    missing = state.get("auth_missing_fields", [])
    if missing:
        state["response_parts"].append(
            "To process your protected request, please provide the missing verification data: "
            + ", ".join(missing)
            + "."
        )
    _append_step(state, step, "completed", "Auth follow-up composed.")
    return state


def handle_protected_intents_node(state: dict[str, Any]) -> dict[str, Any]:
    step = "handle_protected_intents"
    _append_step(state, step, "running", "Processing authenticated intents.")

    protected_intents = state.get("pending_protected_intents", [])
    if not protected_intents:
        _append_step(state, step, "skipped", "No protected intent pending.")
        return state
    if not state.get("auth_verified"):
        _append_step(state, step, "skipped", "Protected intent waiting for auth.")
        return state

    customer_repo = MockCustomerRepository()
    for intent in protected_intents:
        if intent == Intent.METER_READING_SUBMISSION:
            reading = state["entities"].get("meter_reading_kwh")
            if reading is None:
                state["response_parts"].append("Please share your latest meter reading in kWh.")
                continue

            previous = customer_repo.previous_meter_reading(str(state["entities"]["contract_number"]))
            if previous is not None and int(reading) > previous + 1000:
                state["response_parts"].append(
                    f"Your submitted meter reading ({reading} kWh) looks unusually high. "
                    "Please double-check and confirm."
                )
            else:
                state["response_parts"].append(
                    f"Thank you. Your meter reading of {reading} kWh has been recorded successfully."
                )
            state.setdefault("handled_intents", []).append(intent)

        if intent == Intent.CONTRACT_ISSUES:
            state["response_parts"].append(
                "For contract duration, termination, or switching, we can proceed after review and send next steps."
            )
            state.setdefault("handled_intents", []).append(intent)

        if intent == Intent.PERSONAL_DATA_CHANGE:
            state["response_parts"].append(
                "Your personal data change request has been received and is queued for secure processing."
            )
            state.setdefault("handled_intents", []).append(intent)

    state["pending_protected_intents"] = []
    _append_step(state, step, "completed", "Protected intent handling completed.")
    return state


def aggregate_response_node(state: dict[str, Any]) -> dict[str, Any]:
    step = "aggregate_response"
    _append_step(state, step, "running", "Aggregating final customer response.")

    if state["response_parts"]:
        state["final_response"] = (
            "Hello,\n\n"
            + "\n\n".join(state["response_parts"])
            + "\n\nKind regards,\nAI Service Assistant"
        )
    elif state["errors"]:
        state["final_response"] = (
            "Hello,\n\nWe could not process your request due to missing or invalid data. "
            "Please provide more details so we can help.\n\nKind regards,\nAI Service Assistant"
        )
    else:
        state["final_response"] = (
            "Hello,\n\nThank you for your email. Could you please provide a bit more detail "
            "about your request?\n\nKind regards,\nAI Service Assistant"
        )

    _append_step(state, step, "completed", "Final response composed.")
    return state
