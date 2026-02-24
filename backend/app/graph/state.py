from __future__ import annotations

from typing import Any, TypedDict

from app.models.schemas import Intent


class GraphState(TypedDict):
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
