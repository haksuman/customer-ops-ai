from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from app.core.llm import get_llm
from app.domain.auth_policy import AUTH_FIELD_LABELS, get_missing_auth_fields, get_missing_auth_labels, needs_auth, verify_auth
from app.models.schemas import AUTH_REQUIRED_INTENTS, Intent, PendingApproval
from app.services.extractor import detect_intents, extract_entities
from app.services.mock_repos import MockCustomerRepository, MockProductRepository, MockApprovalRepository, MockNotHandledRepository

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
    
    no_auth_intents = [
        intent for intent in state["detected_intents"] 
        if intent not in AUTH_REQUIRED_INTENTS
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

    protected_intents = [
        intent for intent in state["detected_intents"] 
        if intent in AUTH_REQUIRED_INTENTS
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
                customer = customer_repo.get_customer_by_contract(contract_number)
                name = customer["full_name"] if customer else "Customer"
                
                # Requirements template from project_requirements.md (98-111)
                anomaly_template = (
                    f"Dear {name},\n\n"
                    "This is your AI-powered service assistant. While reviewing your meter reading, "
                    f"I noticed that your consumption of {reading} kWh for the recent period appears unusually high.\n\n"
                    "I kindly ask you to double-check the data or let us know the reason for this possible deviation. "
                    "Common reasons may include:\n"
                    "- Construction work (e.g., contractors, drying processes)\n"
                    "- New family members or additional occupants\n"
                    "- New tech equipment, sauna, electric vehicle, etc.\n\n"
                    "Simply reply to this email, and we will get back to you promptly to assist you.\n\n"
                    "Kind Regards"
                )
                state["verbatim_response"] = anomaly_template
            else:
                customer_repo.update_meter_reading(contract_number, int(reading))
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
            # HITL safety check
            llm = get_llm()
            safety_prompt = """Analyze the personal data change request. 
            Is it a simple name change or address update? 
            Or is it dangerous (e.g. requesting to cancel the contract, delete data, or changing to something obviously fake/malicious)?
            
            Return ONLY a JSON object:
            {
                "status": "approved" | "pending" | "dangerous",
                "summary": "Short 1-sentence summary of the request",
                "requested_change": { "field": "new_value" }
            }"""
            
            try:
                safety_res = llm.invoke([
                    SystemMessage(content=safety_prompt),
                    HumanMessage(content=state["latest_message"])
                ])
                
                import json
                import re
                
                # More robust JSON extraction
                content = safety_res.content.strip()
                json_match = re.search(r"\{[\s\S]*\}", content)
                if json_match:
                    content = json_match.group(0)
                
                safety_data = json.loads(content)
                
                if safety_data["status"] == "dangerous":
                    state["response_parts"].append(
                        "We cannot process your personal data change request as it appears to contain invalid or restricted instructions. "
                        "Please contact our support hotline for further assistance."
                    )
                    handled.append(intent)
                elif safety_data["status"] == "approved" and "full_name" in safety_data.get("requested_change", {}):
                    # Auto-approve simple name changes for demo purposes if we wanted to, 
                    # but the requirement says they should go through operator approval.
                    # So we'll force everything to "pending" for the HITL demo.
                    approval_repo = MockApprovalRepository()
                    approval_id = str(uuid.uuid4())
                    pending = PendingApproval(
                        id=approval_id,
                        thread_id=state.get("thread_id", "unknown"),
                        contract_number=contract_number,
                        intent=intent,
                        requested_change=safety_data.get("requested_change", {}),
                        ai_summary=safety_data.get("summary", "Personal data change request"),
                        created_at=datetime.now().isoformat()
                    )
                    approval_repo.add_pending(pending.model_dump())
                    
                    state["response_parts"].append(
                        "Your request for a personal data change has been forwarded to our customer service team for final review. "
                        "A human operator will check the details and apply the changes shortly. You will receive a confirmation once complete."
                    )
                    handled.append(intent)
                else:
                    # Fallback for other types of changes
                    approval_repo = MockApprovalRepository()
                    approval_id = str(uuid.uuid4())
                    pending = PendingApproval(
                        id=approval_id,
                        thread_id=state.get("thread_id", "unknown"),
                        contract_number=contract_number,
                        intent=intent,
                        requested_change=safety_data.get("requested_change", {}),
                        ai_summary=safety_data.get("summary", "Data change request"),
                        created_at=datetime.now().isoformat()
                    )
                    approval_repo.add_pending(pending.model_dump())
                    
                    state["response_parts"].append(
                        "Your data change request has been received and forwarded to a human operator for verification. "
                        "We will notify you as soon as the review is complete."
                    )
                    handled.append(intent)
            except Exception as e:
                logger.error(f"Safety check failed: {e}")
                state["response_parts"].append(
                    "Your personal data change request has been received and is queued for secure processing. "
                    "A support representative will review it shortly."
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

    if state.get("verbatim_response"):
        state["final_response"] = state["verbatim_response"]
        _append_step(state, step, "completed", "Used verbatim response template.")
        return state

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


def fallback_check_node(state: dict[str, Any]) -> dict[str, Any]:
    step = "fallback_check"
    _append_step(state, step, "running", "Checking if the request needs manual handling.")

    detected_intents = state.get("detected_intents", [])
    latest_message = str(state.get("latest_message", "")).lower()
    
    # Logic for fallback:
    # 1. Out-of-scope topics (e.g., tax/legal/accounting questions)
    # 2. No intents detected at all
    # 3. No customer-facing response generated in this run and no auth follow-up pending
    
    requires_manual = False
    reason_code = ""
    ai_log = ""

    out_of_scope_keywords = (
        "tax",
        "taxes",
        "tax declaration",
        "tax deduction",
        "income tax",
        "steuer",
        "steuererklaerung",
        "steuererklärung",
        "accounting advice",
        "legal advice",
        "lawyer",
    )
    if any(keyword in latest_message for keyword in out_of_scope_keywords):
        requires_manual = True
        reason_code = "OUT_OF_SCOPE"
        ai_log = (
            "The message appears to request tax/legal/accounting guidance, "
            "which is outside supported utility customer-service intents."
        )
    elif not detected_intents:
        requires_manual = True
        reason_code = "OUT_OF_SCOPE"
        ai_log = "No clear customer intent could be detected in the email."
    elif (
        not state.get("response_parts")
        and not state.get("auth_missing_fields")
        and not state.get("pending_protected_intents")
    ):
        requires_manual = True
        reason_code = "MANUAL_ACTION_REQUIRED"
        ai_log = (
            f"Detected intents {detected_intents} but no automated response "
            "content was generated for this message."
        )

    if requires_manual:
        state["requires_manual_review"] = True
        state["manual_review_reason_code"] = reason_code
        state["manual_review_log"] = ai_log
        
        # Persist to not-handled queue
        repo = MockNotHandledRepository()
        item = {
            "id": str(uuid.uuid4()),
            "thread_id": state.get("thread_id", "unknown"),
            "original_message": state.get("latest_message", ""),
            "detected_intents": [i.value for i in detected_intents],
            "reason_code": reason_code,
            "ai_log": ai_log,
            "created_at": datetime.now().isoformat(),
            "status": "pending"
        }
        repo.add_item(item)
        
        # Replace auto-generated content so customer receives a clear handoff message only.
        state["response_parts"] = [
            "Thank you for your message. I have forwarded your request to a human support specialist "
            "because it requires manual review. A responsible team member will contact you shortly."
        ]
        _append_step(state, step, "completed", f"Request forwarded to manual queue: {reason_code}.")
    else:
        _append_step(state, step, "completed", "Automated handling is proceeding.")

    return state
