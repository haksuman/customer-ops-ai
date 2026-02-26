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
    requires_manual_review: bool = False
    manual_review_reason: str | None = None


class ThreadStateResponse(BaseModel):
    state: ThreadState


class PendingApproval(BaseModel):
    id: str
    thread_id: str
    contract_number: str
    intent: Intent
    requested_change: dict[str, Any]
    ai_summary: str
    is_dangerous: bool = False
    created_at: str
    customer_info: dict[str, Any] | None = None


class NotHandledEmail(BaseModel):
    id: str
    thread_id: str
    original_message: str
    detected_intents: list[Intent]
    reason_code: str
    ai_log: str
    created_at: str
    status: Literal["pending", "resolved"] = "pending"


class ApprovalListResponse(BaseModel):
    approvals: list[PendingApproval]


class NotHandledEmailListResponse(BaseModel):
    emails: list[NotHandledEmail]


class ProcessingEvent(BaseModel):
    type: str  # message_processed, auto_handled, manual_forwarded, approval_approved, approval_rejected, manual_resolved
    timestamp: str
    thread_id: str
    intents: list[Intent]
    metadata: dict[str, Any] = Field(default_factory=dict)


class DashboardKpis(BaseModel):
    total_processed: int
    auto_handled: int
    manual_forwarded: int
    approvals: int
    rejections: int
    automation_rate: float


class DashboardTimeseriesPoint(BaseModel):
    date: str
    processed: int
    auto_handled: int
    manual_forwarded: int


class DashboardIntentBreakdown(BaseModel):
    intent: str
    count: int


class DashboardReasonBreakdown(BaseModel):
    reason: str
    count: int


class DashboardResponse(BaseModel):
    kpis: DashboardKpis
    timeseries: list[DashboardTimeseriesPoint]
    intents: list[DashboardIntentBreakdown]
    reasons: list[DashboardReasonBreakdown]
