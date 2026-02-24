from __future__ import annotations

from copy import deepcopy

from fastapi import APIRouter, HTTPException

from app.core.logging import thread_id_ctx
from app.graph.workflow import build_workflow
from app.models.schemas import (
    ApprovalListResponse,
    Message,
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

    return ProcessMessageResponse(
        thread_id=thread.thread_id,
        assistant_reply=thread.final_response,
        intents=thread.detected_intents,
        auth_verified=thread.auth_verified,
        entities=thread.entities,
        workflow_steps=thread.workflow_steps,
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
    return {"status": "success"}


@router.get("/threads/{thread_id}", response_model=ThreadStateResponse)
async def get_thread(thread_id: str) -> ThreadStateResponse:
    thread = THREAD_STORE.get(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return ThreadStateResponse(state=thread)
