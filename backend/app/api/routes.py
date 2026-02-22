from __future__ import annotations

from copy import deepcopy

from fastapi import APIRouter, HTTPException

from app.core.logging import thread_id_ctx
from app.graph.workflow import build_workflow
from app.models.schemas import (
    Message,
    ProcessMessageRequest,
    ProcessMessageResponse,
    ThreadState,
    ThreadStateResponse,
    WorkflowStep,
)

router = APIRouter(prefix="/api", tags=["copilot"])

THREAD_STORE: dict[str, ThreadState] = {}


def _initial_state(thread_id: str) -> ThreadState:
    return ThreadState(thread_id=thread_id)


def _to_graph_input(state: ThreadState, latest_message: str) -> dict:
    return {
        "latest_message": latest_message,
        "detected_intents": [],
        "pending_protected_intents": state.pending_protected_intents.copy(),
        "entities": deepcopy(state.entities),
        "auth_verified": state.auth_verified,
        "auth_missing_fields": [],
        "response_parts": [],
        "workflow_steps": [],
        "errors": [],
        "final_response": "",
        "handled_intents": [],
    }


@router.post("/messages/process", response_model=ProcessMessageResponse)
async def process_message(payload: ProcessMessageRequest) -> ProcessMessageResponse:
    thread_id_ctx.set(payload.thread_id)
    thread = THREAD_STORE.get(payload.thread_id, _initial_state(payload.thread_id))
    thread.messages.append(Message(role="customer", content=payload.message))

    workflow = build_workflow()
    graph_state = workflow.invoke(_to_graph_input(thread, payload.message))

    thread.latest_message = payload.message
    thread.detected_intents = graph_state["detected_intents"]
    thread.pending_protected_intents = graph_state["pending_protected_intents"]
    thread.entities = graph_state["entities"]
    thread.auth_verified = graph_state["auth_verified"]
    thread.auth_missing_fields = graph_state["auth_missing_fields"]
    thread.workflow_steps = [WorkflowStep(**step) for step in graph_state["workflow_steps"]]
    thread.errors = graph_state["errors"]
    thread.final_response = graph_state["final_response"]
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


@router.get("/threads/{thread_id}", response_model=ThreadStateResponse)
async def get_thread(thread_id: str) -> ThreadStateResponse:
    thread = THREAD_STORE.get(thread_id)
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    return ThreadStateResponse(state=thread)
