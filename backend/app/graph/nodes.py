from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import get_llm
from app.domain.auth_policy import AUTH_FIELD_LABELS, get_missing_auth_fields, get_missing_auth_labels, needs_auth, verify_auth
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
    
    handled = state.get("handled_intents", [])
    no_auth_intents = [
        intent for intent in state["detected_intents"] 
        if intent not in AUTH_REQUIRED_INTENTS and intent not in handled
    ]
    
    if not no_auth_intents:
        _append_step(state, step, "skipped", "No new public intents detected.")
        return state

    product_repo = MockProductRepository()
    for intent in no_auth_intents:
        if intent == Intent.PRODUCT_INFO_REQUEST:
            state["response_parts"].append(product_repo.get_tariff_info("dynamic-tariff"))
            state.setdefault("handled_intents", []).append(intent)
        elif intent == Intent.GENERAL_FEEDBACK:
            state["response_parts"].append("Thank you for your feedback. We appreciate you reaching out.")
            state.setdefault("handled_intents", []).append(intent)

    _append_step(state, step, "completed", f"Handled {len(no_auth_intents)} no-auth intent(s).")
    return state


def auth_policy_node(state: dict[str, Any]) -> dict[str, Any]:
    step = "auth_policy"
    _append_step(state, step, "running", "Evaluating whether authentication is required.")

    handled = state.get("handled_intents", [])
    protected_intents = [
        intent for intent in state["detected_intents"] 
        if intent in AUTH_REQUIRED_INTENTS and intent not in handled
    ]
    
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
        labels = get_missing_auth_labels(state["entities"])
        _append_step(state, step, "completed", f"Missing fields: {', '.join(labels)}.")
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
        labels = [AUTH_FIELD_LABELS.get(f, f) for f in missing]
        bullet_list = "\n".join(f"- {label}" for label in labels)
        state["response_parts"].append(
            "To process your request, we need the following verification details:\n"
            + bullet_list
            + "\n\nSimply reply to this email and we will get back to you promptly."
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
    contract_number = str(state["entities"].get("contract_number", ""))
    handled = state.setdefault("handled_intents", [])
    for intent in protected_intents:
        if intent == Intent.METER_READING_SUBMISSION:
            reading = state["entities"].get("meter_reading_kwh")
            if reading is None:
                state["response_parts"].append("Please share your latest meter reading in kWh.")
                continue

            submitted_meter = state["entities"].get("meter_number")
            if submitted_meter:
                expected_meter = customer_repo.get_meter_number(contract_number)
                if expected_meter and submitted_meter != expected_meter:
                    state["response_parts"].append(
                        f"The meter number you provided ({submitted_meter}) does not match "
                        "the meter registered on your account. Please verify and resubmit."
                    )
                    continue

            previous = customer_repo.previous_meter_reading(contract_number)
            if previous is not None and int(reading) > previous + 1000:
                state["response_parts"].append(
                    f"Your submitted meter reading ({reading} kWh) looks unusually high "
                    f"compared to your previous reading ({previous} kWh). "
                    "Please double-check and confirm, or let us know if there is a reason for this deviation."
                )
            else:
                state["response_parts"].append(
                    f"Thank you. Your meter reading of {reading} kWh has been recorded successfully."
                )
            handled.append(intent)

        elif intent == Intent.CONTRACT_ISSUES:
            state["response_parts"].append(
                "We have received your contract query. Our team will review your contract details "
                "and send you the next steps regarding duration, termination, or switching within one business day."
            )
            handled.append(intent)

        elif intent == Intent.PERSONAL_DATA_CHANGE:
            state["response_parts"].append(
                "Your personal data change request has been received and is queued for secure processing. "
                "Changes will be applied within 2 business days and you will receive a confirmation."
            )
            handled.append(intent)

    # Filter out successfully handled intents from pending
    state["pending_protected_intents"] = [
        intent for intent in state.get("pending_protected_intents", [])
        if intent not in handled
    ]
    _append_step(state, step, "completed", "Protected intent handling completed.")
    return state


def aggregate_response_node(state: dict[str, Any]) -> dict[str, Any]:
    step = "aggregate_response"
    _append_step(state, step, "running", "Aggregating final customer response.")

    if state["response_parts"]:
        content_block = "\n\n".join(state["response_parts"])
    elif state["errors"]:
        content_block = (
            "We could not fully process the request due to missing or invalid data. "
            "Ask the customer to provide more details."
        )
    else:
        content_block = "Ask the customer to clarify their request."

    system = (
        "You are a professional customer service assistant for a German energy utility. "
        "Write a polite, concise, and empathetic email reply to the customer. "
        "Use the provided content points as the body. "
        "Start with 'Hello,' and end with 'Kind regards,\nAI Service Assistant'. "
        "Do not add new information beyond what is provided."
    )
    user = f"Content points to include in the reply:\n\n{content_block}"

    try:
        llm = get_llm()
        response = llm.invoke([SystemMessage(content=system), HumanMessage(content=user)])
        state["final_response"] = response.content
    except Exception as exc:
        logger.exception("aggregate_llm_failed", extra={"node": step})
        state["final_response"] = (
            "Hello,\n\n"
            + content_block
            + "\n\nKind regards,\nAI Service Assistant"
        )
        state["errors"].append(f"LLM aggregation failed, used fallback: {exc}")

    _append_step(state, step, "completed", "Final response composed.")
    return state
