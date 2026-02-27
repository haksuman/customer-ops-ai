from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Query

from app.core.logging import thread_id_ctx
from app.graph.workflow import build_workflow
from app.models.schemas import (
    ApprovalListResponse,
    Customer,
    CustomerListResponse,
    DashboardResponse,
    DashboardKpis,
    DashboardTimeseriesPoint,
    DashboardIntentBreakdown,
    DashboardReasonBreakdown,
    Message,
    NotHandledEmail,
    NotHandledEmailListResponse,
    PendingApproval,
    ProcessMessageRequest,
    ProcessMessageResponse,
    ThreadState,
    ThreadStateResponse,
    WorkflowStep,
)
from app.services.mock_repos import (
    MockApprovalRepository,
    MockCustomerRepository,
    MockEventRepository,
    MockNotHandledRepository,
)

router = APIRouter(prefix="/api", tags=["copilot"])

THREAD_STORE: dict[str, ThreadState] = {}


def _initial_state(thread_id: str) -> ThreadState:
    return ThreadState(thread_id=thread_id)


def _to_graph_input(state: ThreadState, latest_message: str) -> dict:
    return {
        "thread_id": state.thread_id,
        "latest_message": latest_message,
        "detected_intents": [],
        "pending_protected_intents": state.pending_protected_intents.copy(),
        "entities": deepcopy(state.entities),
        "auth_verified": state.auth_verified,
        "auth_missing_fields": [] if state.auth_verified else state.auth_missing_fields.copy(),
        "response_parts": [],
        "workflow_steps": [],
        "errors": [],
        "final_response": "",
        "handled_intents": state.handled_intents.copy(),
        "requires_manual_review": False,
        "manual_review_reason_code": "",
        "manual_review_log": "",
        "verbatim_response": None,
    }


@router.post("/messages/process", response_model=ProcessMessageResponse)
async def process_message(payload: ProcessMessageRequest) -> ProcessMessageResponse:
    thread_id_ctx.set(payload.thread_id)
    thread = THREAD_STORE.get(payload.thread_id, _initial_state(payload.thread_id))
    thread.messages.append(Message(role="customer", content=payload.message))

    workflow = build_workflow()
    graph_state = workflow.invoke(_to_graph_input(thread, payload.message))

    thread.latest_message = payload.message
    thread.detected_intents = graph_state.get("detected_intents", [])
    thread.pending_protected_intents = graph_state.get("pending_protected_intents", [])
    thread.handled_intents = graph_state.get("handled_intents", [])
    thread.entities = graph_state.get("entities", {})
    thread.auth_verified = graph_state.get("auth_verified", False)
    thread.auth_missing_fields = graph_state.get("auth_missing_fields", [])
    thread.workflow_steps = [WorkflowStep(**step) for step in graph_state.get("workflow_steps", [])]
    thread.errors = graph_state.get("errors", [])
    thread.final_response = graph_state.get("final_response", "")
    thread.messages.append(Message(role="assistant", content=thread.final_response))

    THREAD_STORE[payload.thread_id] = thread

    # Emit event
    event_repo = MockEventRepository()
    outcome = "manual_forwarded" if graph_state.get("requires_manual_review") else "auto_handled"
    event_repo.add_event({
        "type": "message_processed",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "thread_id": payload.thread_id,
        "intents": [i.value for i in thread.detected_intents],
        "metadata": {
            "outcome": outcome,
            "reason": graph_state.get("manual_review_reason_code")
        }
    })

    return ProcessMessageResponse(
        thread_id=thread.thread_id,
        assistant_reply=thread.final_response,
        intents=thread.detected_intents,
        auth_verified=thread.auth_verified,
        entities=thread.entities,
        workflow_steps=thread.workflow_steps,
        requires_manual_review=graph_state.get("requires_manual_review", False),
        manual_review_reason=graph_state.get("manual_review_reason_code"),
    )


@router.get("/approvals", response_model=ApprovalListResponse)
async def list_approvals() -> ApprovalListResponse:
    repo = MockApprovalRepository()
    cust_repo = MockCustomerRepository()
    records = repo.list_pending()
    
    approvals = []
    for r in records:
        approval = PendingApproval(**r)
        # Enrich with current customer info
        approval.customer_info = cust_repo.get_customer_by_contract(approval.contract_number)
        approvals.append(approval)
        
    return ApprovalListResponse(approvals=approvals)


@router.post("/approvals/{approval_id}/approve")
async def approve_change(approval_id: str):
    approval_repo = MockApprovalRepository()
    approval = approval_repo.get_by_id(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    # 1. Update customer data
    cust_repo = MockCustomerRepository()
    changes = approval.get("requested_change", {})
    if "full_name" in changes:
        cust_repo.update_customer_name(approval["contract_number"], changes["full_name"])
    
    # 2. Notify thread
    thread = THREAD_STORE.get(approval["thread_id"])
    if thread:
        thread.messages.append(Message(
            role="assistant", 
            content=f"APPROVED: Your request for a {approval['intent']} has been reviewed and approved by an operator. The changes have been applied to your account."
        ))
    
    # 3. Remove from pending
    approval_repo.remove_pending(approval_id)

    # Emit event
    event_repo = MockEventRepository()
    event_repo.add_event({
        "type": "approval_approved",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "thread_id": approval["thread_id"],
        "intents": [approval["intent"]],
        "metadata": {"approval_id": approval_id}
    })

    return {"status": "success"}


@router.post("/approvals/{approval_id}/reject")
async def reject_change(approval_id: str):
    approval_repo = MockApprovalRepository()
    approval = approval_repo.get_by_id(approval_id)
    if not approval:
        raise HTTPException(status_code=404, detail="Approval request not found")
    
    # 1. Notify thread
    thread = THREAD_STORE.get(approval["thread_id"])
    if thread:
        thread.messages.append(Message(
            role="assistant", 
            content=f"REJECTED: Your request for a {approval['intent']} was reviewed by an operator and could not be approved at this time. Please contact support for more details."
        ))
    
    # 2. Remove from pending
    approval_repo.remove_pending(approval_id)

    # Emit event
    event_repo = MockEventRepository()
    event_repo.add_event({
        "type": "approval_rejected",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "thread_id": approval["thread_id"],
        "intents": [approval["intent"]],
        "metadata": {"approval_id": approval_id}
    })

    return {"status": "success"}


@router.get("/not-handled-emails", response_model=NotHandledEmailListResponse)
async def list_not_handled_emails() -> NotHandledEmailListResponse:
    repo = MockNotHandledRepository()
    records = repo.list_pending()
    emails = [NotHandledEmail(**r) for r in records]
    return NotHandledEmailListResponse(emails=emails)


@router.post("/not-handled-emails/{item_id}/resolve")
async def resolve_not_handled_email(item_id: str):
    repo = MockNotHandledRepository()
    item = repo.get_by_id(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Email record not found")
    
    # Notify thread if it exists
    thread = THREAD_STORE.get(item["thread_id"])
    if thread:
        thread.messages.append(Message(
            role="assistant",
            content="RESOLVED: This request was manually reviewed and resolved by an operator."
        ))
    
    repo.mark_resolved(item_id)

    # Emit event
    event_repo = MockEventRepository()
    event_repo.add_event({
        "type": "manual_resolved",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "thread_id": item["thread_id"],
        "intents": item["detected_intents"],
        "metadata": {"item_id": item_id, "reason_code": item["reason_code"]}
    })

    return {"status": "success"}


@router.get("/dashboard", response_model=DashboardResponse)
async def get_dashboard_stats(window: str = Query("7d", regex="^(today|7d|30d|90d)$")) -> DashboardResponse:
    event_repo = MockEventRepository()
    
    # Calculate start time
    now = datetime.now(timezone.utc)
    if window == "today":
        start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif window == "7d":
        start_time = now - timedelta(days=7)
    elif window == "30d":
        start_time = now - timedelta(days=30)
    else:  # 90d
        start_time = now - timedelta(days=90)
        
    events = event_repo.get_events_after(start_time)
    
    # KPI Calculations
    total_processed = sum(1 for e in events if e["type"] == "message_processed")
    auto_handled = sum(1 for e in events if e["type"] == "message_processed" and e["metadata"].get("outcome") == "auto_handled")
    manual_forwarded = sum(1 for e in events if e["type"] == "message_processed" and e["metadata"].get("outcome") == "manual_forwarded")
    approvals = sum(1 for e in events if e["type"] == "approval_approved")
    rejections = sum(1 for e in events if e["type"] == "approval_rejected")
    
    automation_rate = (auto_handled / total_processed * 100) if total_processed > 0 else 0
    
    # Timeseries (Grouped by Day)
    timeseries_map: dict[str, dict] = {}
    
    # Initialize all days in window to 0
    curr = start_time
    while curr <= now:
        day_str = curr.strftime("%Y-%m-%d")
        timeseries_map[day_str] = {"date": day_str, "processed": 0, "auto_handled": 0, "manual_forwarded": 0}
        curr += timedelta(days=1)
        
    for e in events:
        if e["type"] == "message_processed":
            day_str = datetime.fromisoformat(e["timestamp"].replace("Z", "+00:00")).strftime("%Y-%m-%d")
            if day_str in timeseries_map:
                timeseries_map[day_str]["processed"] += 1
                if e["metadata"].get("outcome") == "auto_handled":
                    timeseries_map[day_str]["auto_handled"] += 1
                else:
                    timeseries_map[day_str]["manual_forwarded"] += 1
                    
    timeseries = sorted(timeseries_map.values(), key=lambda x: x["date"])
    
    # Intent Breakdown
    intent_map: dict[str, int] = {}
    for e in events:
        if e["type"] == "message_processed":
            for intent in e["intents"]:
                intent_map[intent] = intent_map.get(intent, 0) + 1
    
    intents = [DashboardIntentBreakdown(intent=k, count=v) for k, v in intent_map.items()]
    
    # Reason Breakdown
    reason_map: dict[str, int] = {}
    for e in events:
        if e["type"] == "message_processed" and e["metadata"].get("outcome") == "manual_forwarded":
            reason = e["metadata"].get("reason", "UNKNOWN")
            reason_map[reason] = reason_map.get(reason, 0) + 1
            
    reasons = [DashboardReasonBreakdown(reason=k, count=v) for k, v in reason_map.items()]
    
    return DashboardResponse(
        kpis=DashboardKpis(
            total_processed=total_processed,
            auto_handled=auto_handled,
            manual_forwarded=manual_forwarded,
            approvals=approvals,
            rejections=rejections,
            automation_rate=round(automation_rate, 1)
        ),
        timeseries=timeseries,
        intents=intents,
        reasons=reasons
    )


@router.get("/threads/{thread_id}", response_model=ThreadStateResponse)
async def get_thread(thread_id: str) -> ThreadStateResponse:
    thread = THREAD_STORE.get(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return ThreadStateResponse(state=thread)


@router.get("/customers", response_model=CustomerListResponse)
async def list_customers() -> CustomerListResponse:
    repo = MockCustomerRepository()
    customers = [Customer(**r) for r in repo.list_all()]
    return CustomerListResponse(customers=customers)
