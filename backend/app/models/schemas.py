from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Intent(str, Enum):
    METER_READING_SUBMISSION = "MeterReadingSubmission"
    PERSONAL_DATA_CHANGE = "PersonalDataChange"
    CONTRACT_ISSUES = "ContractIssues"
    PRODUCT_INFO_REQUEST = "ProductInfoRequest"
    GENERAL_FEEDBACK = "GeneralFeedback"


AUTH_REQUIRED_INTENTS = {
    Intent.METER_READING_SUBMISSION,
    Intent.PERSONAL_DATA_CHANGE,
    Intent.CONTRACT_ISSUES,
}


class Message(BaseModel):
    role: Literal["customer", "assistant"]
    content: str


class WorkflowStep(BaseModel):
    name: str
    status: Literal["pending", "running", "completed", "skipped", "failed"]
    detail: str = ""


class ThreadState(BaseModel):
    thread_id: str
    messages: list[Message] = Field(default_factory=list)
    latest_message: str = ""
    detected_intents: list[Intent] = Field(default_factory=list)
    pending_protected_intents: list[Intent] = Field(default_factory=list)
    handled_intents: list[Intent] = Field(default_factory=list)
    entities: dict[str, Any] = Field(default_factory=dict)
    auth_verified: bool = False
    auth_missing_fields: list[str] = Field(default_factory=list)
    response_parts: list[str] = Field(default_factory=list)
    workflow_steps: list[WorkflowStep] = Field(default_factory=list)
    final_response: str = ""
    errors: list[str] = Field(default_factory=list)


class ProcessMessageRequest(BaseModel):
    thread_id: str = Field(min_length=1)
    message: str = Field(min_length=1)


class ProcessMessageResponse(BaseModel):
    thread_id: str
    assistant_reply: str
    intents: list[Intent]
    auth_verified: bool
    entities: dict[str, Any]
    workflow_steps: list[WorkflowStep]


class ThreadStateResponse(BaseModel):
    state: ThreadState
