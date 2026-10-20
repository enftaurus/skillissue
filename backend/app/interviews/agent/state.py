from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field

class CandidateClaim(BaseModel):
    """
    Candidate technical claim or assertion linked to transcript evidence.
    """
    claim: str = Field(description="Verbatim or summarized technical claim made by candidate")
    topic: str = Field(description="Rubric competency or topic domain")
    message_id: Optional[str] = Field(default=None, description="InterviewMessage ID where claim was asserted")
    turn: int = Field(default=0, description="Turn index of assertion")
    verification_status: str = Field(default="unverified", description="'unverified' | 'probed' | 'verified' | 'refuted'")

class AdaptiveDecision(BaseModel):
    """
    Validated structured decision on next interview progression.
    Determines whether to ask a clarifying follow-up, pivot to a new topic,
    or adjust difficulty based on candidate evidence and topic lifecycle status.
    """
    action: str = Field(
        description="One of: 'ask_follow_up', 'next_topic', 'increase_difficulty', 'decrease_difficulty', 'wrapup'"
    )
    reason: str = Field(description="Concrete engineering rationale for the chosen transition.")
    difficulty_delta: int = Field(default=0, description="-1 to lower difficulty, +1 to increase difficulty, 0 to maintain")
    suggested_topic: Optional[str] = Field(default=None, description="Topic to pivot to if changing topics")
    identified_evidence: Optional[str] = Field(default=None, description="Evidence or claim extracted from candidate answer")
    topic_status: Optional[str] = Field(default=None, description="Status update for current topic: 'assessed' | 'needs_follow_up' | 'in_progress'")

class InterviewAgentState(TypedDict, total=False):
    """
    Typed state container for the LangGraph interview agent.
    Maintains bounded short-term conversational context, rolling summary,
    and deterministic progression metrics across explicit topic lifecycle states.
    """
    interview_id: str
    user_id: str
    category: str
    target_role: str
    difficulty: str
    domain_skills: List[str]
    jd_context: Optional[str]
    resume_context: Optional[str]
    current_topic: str
    covered_topics: List[str]
    topic_statuses: Dict[str, str]  # topic name -> 'not_started' | 'in_progress' | 'assessed' | 'needs_follow_up'
    pending_follow_up: bool
    running_summary: str
    recent_messages: List[Dict[str, str]]
    candidate_evidence: List[Dict[str, Any]]
    turn_count: int
    max_turns: int
    next_action: str
    decision_reason: str
    latest_candidate_answer: str
    latest_candidate_message_id: Optional[str]
    client_turn_id: Optional[str]
    generated_question: str
    question_metadata: Dict[str, Any]
    phase: str
    last_error: Optional[str]
