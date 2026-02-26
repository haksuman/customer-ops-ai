from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from app.graph.nodes import (
    aggregate_response_node,
    auth_policy_node,
    compose_auth_request_node,
    extract_and_detect_node,
    fallback_check_node,
    handle_no_auth_intents_node,
    handle_protected_intents_node,
)
from app.graph.state import GraphState


def _route_after_auth(state: GraphState) -> str:
    if state.get("pending_protected_intents") and not state.get("auth_verified"):
        return "compose_auth_request"
    return "handle_protected_intents"


@lru_cache(maxsize=1)
def build_workflow():
    graph = StateGraph(GraphState)
    graph.add_node("extract_and_detect", extract_and_detect_node)
    graph.add_node("handle_no_auth_intents", handle_no_auth_intents_node)
    graph.add_node("auth_policy", auth_policy_node)
    graph.add_node("compose_auth_request", compose_auth_request_node)
    graph.add_node("handle_protected_intents", handle_protected_intents_node)
    graph.add_node("fallback_check", fallback_check_node)
    graph.add_node("aggregate_response", aggregate_response_node)

    graph.add_edge(START, "extract_and_detect")
    graph.add_edge("extract_and_detect", "handle_no_auth_intents")
    graph.add_edge("handle_no_auth_intents", "auth_policy")
    graph.add_conditional_edges(
        "auth_policy",
        _route_after_auth,
        {
            "compose_auth_request": "compose_auth_request",
            "handle_protected_intents": "handle_protected_intents",
        },
    )
    graph.add_edge("compose_auth_request", "fallback_check")
    graph.add_edge("handle_protected_intents", "fallback_check")
    graph.add_edge("fallback_check", "aggregate_response")
    graph.add_edge("aggregate_response", END)

    return graph.compile()
