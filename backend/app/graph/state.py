from __future__ import annotations

from typing import Any, TypedDict

from app.models.schemas import Intent


class GraphState(TypedDict):
    thread_id: str
    latest_message: str
    detected_intents: list[Intent]
    pending_protected_intents: list[Intent]
    entities: dict[str, Any]
    auth_verified: bool
    auth_missing_fields: list[str]
    response_parts: list[str]
    workflow_steps: list[dict[str, str]]
    final_response: str
    errors: list[str]
    handled_intents: list[Intent]
    requires_manual_review: bool
    manual_review_reason_code: str
    manual_review_log: str
    verbatim_response: str | None
