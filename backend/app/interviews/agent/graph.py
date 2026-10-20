from typing import Optional
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.base import BaseCheckpointSaver
from backend.app.interviews.agent.state import InterviewAgentState
from backend.app.interviews.agent.nodes import (
    prepare_context_node,
    assess_candidate_turn_node,
    generate_question_node,
    wrapup_interview_node,
)

def route_after_assessment(state: InterviewAgentState) -> str:
    """
    Conditional routing edge after assessing candidate answer.
    Routes to wrapup if question budget or termination condition met,
    otherwise routes to adaptive question generation.
    """
    if state.get("next_action") == "wrapup":
        return "wrapup_interview"
    return "generate_question"

def create_interview_graph(checkpointer: Optional[BaseCheckpointSaver] = None):
    """
    Constructs and compiles the stateful LangGraph interview workflow.
    """
    workflow = StateGraph(InterviewAgentState)

    # Register workflow nodes
    workflow.add_node("prepare_context", prepare_context_node)
    workflow.add_node("assess_candidate_turn", assess_candidate_turn_node)
    workflow.add_node("generate_question", generate_question_node)
    workflow.add_node("wrapup_interview", wrapup_interview_node)

    # Sequence edges
    workflow.add_edge(START, "prepare_context")
    workflow.add_edge("prepare_context", "assess_candidate_turn")

    # Conditional decision routing
    workflow.add_conditional_edges(
        "assess_candidate_turn",
        route_after_assessment,
        {
            "wrapup_interview": "wrapup_interview",
            "generate_question": "generate_question",
        },
    )

    workflow.add_edge("generate_question", END)
    workflow.add_edge("wrapup_interview", END)

    return workflow.compile(checkpointer=checkpointer)
