from typing import Any, Dict, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from backend.app.interviews.agent.state import InterviewAgentState, AdaptiveDecision
from backend.app.interviews.prompts import build_interviewer_system_prompt
from backend.app.core.logging import logger

MAX_RECENT_TURNS = 6  # Last 3 user + 3 assistant turns

def prepare_context_node(state: InterviewAgentState) -> Dict[str, Any]:
    """
    Constructs bounded short-term conversational context and updates the running summary.
    Prevents token bloat while preserving critical candidate claims and covered topics.
    """
    messages = state.get("recent_messages", [])
    running_summary = state.get("running_summary", "")
    covered_topics = list(state.get("covered_topics", []))
    current_topic = state.get("current_topic", "")

    if current_topic and current_topic not in covered_topics:
        covered_topics.append(current_topic)

    # Bound recent messages to last MAX_RECENT_TURNS
    bounded_messages = messages[-MAX_RECENT_TURNS:] if len(messages) > MAX_RECENT_TURNS else messages

    # Update running summary when conversation grows beyond recent window
    if len(messages) > MAX_RECENT_TURNS and not running_summary:
        user_claims = [m["content"] for m in messages if m.get("role") == "user"]
        running_summary = f"Covered topics: {', '.join(covered_topics)}. Key candidate claims: {' | '.join(user_claims[:3])}"

    return {
        "recent_messages": bounded_messages,
        "running_summary": running_summary,
        "covered_topics": covered_topics,
    }

async def assess_candidate_turn_node(state: InterviewAgentState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """
    Evaluates candidate's latest response and deterministically decides next action
    (follow-up, topic transition, difficulty adjustment, or interview wrapup).
    """
    turn_count = state.get("turn_count", 0)
    max_turns = state.get("max_turns", 8)
    latest_answer = state.get("latest_candidate_answer", "").strip()
    current_difficulty = state.get("difficulty", "intermediate")
    current_topic = state.get("current_topic", "")
    domain_skills = state.get("domain_skills", [])
    covered_topics = state.get("covered_topics", [])

    # Check maximum turn limit budget
    if turn_count >= max_turns:
        return {
            "next_action": "wrapup",
            "decision_reason": f"Maximum question budget ({max_turns} turns) reached.",
            "pending_follow_up": False,
        }

    # Attempt structured decision via model client if available in config
    cfg = config or {}
    model = cfg.get("configurable", {}).get("model")
    decision: Optional[AdaptiveDecision] = None

    if model and hasattr(model, "with_structured_output"):
        try:
            structured_evaluator = model.with_structured_output(AdaptiveDecision)
            eval_prompt = (
                f"Candidate Answer: '{latest_answer}'\n"
                f"Current Topic: {current_topic}, Difficulty: {current_difficulty}.\n"
                "Evaluate whether candidate made an unverified claim requiring follow-up, "
                "or whether we should change topic or adjust difficulty."
            )
            decision = await structured_evaluator.ainvoke([HumanMessage(content=eval_prompt)])
        except Exception as e:
            logger.info(f"Model structured evaluation skipped, using deterministic rules: {e}")

    # Fallback to deterministic evaluation rules
    if not decision:
        answer_lower = latest_answer.lower()
        if any(w in answer_lower for w in ["redis", "faster", "10x", "improved", "cache", "scale"]):
            action = "ask_follow_up"
            reason = "Candidate made an unverified latency/scaling claim. Probe measurement methodology."
            difficulty_delta = 0
        elif any(w in answer_lower for w in ["fail", "error", "struggle", "don't know", "unsure"]):
            action = "decrease_difficulty"
            reason = "Candidate encountered difficulty with previous concept."
            difficulty_delta = -1
        elif any(w in answer_lower for w in ["distributed", "raft", "paxos", "saga", "concurrency"]):
            action = "increase_difficulty"
            reason = "Candidate demonstrated strong grasp of distributed system primitives."
            difficulty_delta = 1
        elif len(covered_topics) < len(domain_skills):
            action = "next_topic"
            reason = "Sufficient depth explored on current topic. Progressing through rubric competencies."
            difficulty_delta = 0
        else:
            action = "ask_follow_up"
            reason = "Probing edge cases and trade-offs."
            difficulty_delta = 0

        decision = AdaptiveDecision(
            action=action,
            reason=reason,
            difficulty_delta=difficulty_delta,
        )

    # Calculate next difficulty
    diff_levels = ["beginner", "intermediate", "advanced", "staff"]
    try:
        curr_idx = diff_levels.index(current_difficulty)
    except ValueError:
        curr_idx = 1
    new_idx = max(0, min(len(diff_levels) - 1, curr_idx + decision.difficulty_delta))
    new_difficulty = diff_levels[new_idx]

    # Calculate next topic
    new_topic = current_topic
    if decision.action == "next_topic":
        remaining = [s for s in domain_skills if s not in covered_topics]
        new_topic = remaining[0] if remaining else (domain_skills[0] if domain_skills else current_topic)

    return {
        "next_action": decision.action,
        "decision_reason": decision.reason,
        "difficulty": new_difficulty,
        "current_topic": new_topic,
        "pending_follow_up": decision.action == "ask_follow_up",
    }

async def generate_question_node(state: InterviewAgentState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """
    Generates the next technical interview question or follow-up question.
    Enforces Gilfoyle-level engineering precision: short, dry, skeptical, zero praise.
    """
    cfg = config or {}
    model = cfg.get("configurable", {}).get("model")
    if not model:
        raise ValueError("Model client must be provided in graph configurable parameters.")

    next_action = state.get("next_action", "next_topic")
    current_topic = state.get("current_topic", "System Architecture")
    difficulty = state.get("difficulty", "intermediate")
    category = state.get("category", "technical")
    target_role = state.get("target_role", "Software Engineer")
    domain_skills = state.get("domain_skills", [])
    recent_messages = state.get("recent_messages", [])
    running_summary = state.get("running_summary", "")
    latest_answer = state.get("latest_candidate_answer", "")
    turn_count = state.get("turn_count", 0)

    system_prompt = build_interviewer_system_prompt(
        category=category,
        target_role=target_role,
        difficulty=difficulty,
        domain_skills=domain_skills,
    )

    if running_summary:
        system_prompt += f"\n\nContext from earlier in this interview:\n{running_summary}"

    # Build prompt messages
    prompt_messages = [SystemMessage(content=system_prompt)]
    for m in recent_messages:
        if m.get("role") == "user":
            prompt_messages.append(HumanMessage(content=m.get("content", "")))
        elif m.get("role") == "assistant":
            prompt_messages.append(AIMessage(content=m.get("content", "")))

    if next_action == "ask_follow_up":
        instruction = (
            f"The candidate said: '{latest_answer}'. "
            "Ask exactly ONE direct follow-up probing concrete implementation details, numbers, or trade-offs. "
            "Under 3 sentences. No praise."
        )
    elif next_action == "increase_difficulty":
        instruction = (
            f"Candidate handled the previous question well. Increase technical rigor to {difficulty} level on {current_topic}. "
            "Ask exactly ONE challenging architectural or edge-case question. Under 3 sentences. No praise."
        )
    elif next_action == "decrease_difficulty":
        instruction = (
            f"Candidate struggled with low-level details. Ask a more fundamental {difficulty}-level question on {current_topic}. "
            "Under 3 sentences. No praise."
        )
    else:
        instruction = (
            f"Pivot to the topic of '{current_topic}' at {difficulty} level. "
            "Ask exactly ONE concrete engineering question testing system design or implementation trade-offs. "
            "Under 3 sentences. No praise."
        )

    prompt_messages.append(HumanMessage(content=instruction))

    response = await model.ainvoke(prompt_messages)
    question_text = response.content.strip()

    # Fallback sanity filter
    if not question_text:
        question_text = f"Looking at {current_topic}, what failure modes did you actively engineer around in production?"

    is_follow_up = next_action == "ask_follow_up"

    return {
        "generated_question": question_text,
        "question_metadata": {
            "topic": current_topic,
            "difficulty": difficulty,
            "is_follow_up": is_follow_up,
            "action": next_action,
        },
        "turn_count": turn_count + 1,
        "phase": "active",
    }

async def wrapup_interview_node(state: InterviewAgentState) -> Dict[str, Any]:
    """
    Concludes the interview when turn budget or duration is reached.
    """
    conclusion_text = (
        "That concludes our interview session. Thank you for your concrete explanations and trade-off walkthroughs. "
        "We now have enough diagnostic data to assess your engineering readiness across all rubric dimensions."
    )
    return {
        "generated_question": conclusion_text,
        "question_metadata": {
            "topic": "Wrapup",
            "difficulty": state.get("difficulty", "intermediate"),
            "is_follow_up": False,
            "action": "wrapup",
        },
        "phase": "completed",
    }
