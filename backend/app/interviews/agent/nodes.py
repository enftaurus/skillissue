from typing import Any, Dict, List, Optional
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.runnables import RunnableConfig
from backend.app.interviews.agent.state import InterviewAgentState, AdaptiveDecision
from backend.app.interviews.prompts import build_interviewer_system_prompt
from backend.app.core.logging import logger

MAX_RECENT_TURNS = 6  # Sliding window of last 6 messages (3 user + 3 assistant turns)

def prepare_context_node(state: InterviewAgentState) -> Dict[str, Any]:
    """
    Constructs bounded short-term conversational context and continuously updates
    the rolling summary. Earlier messages falling outside the sliding 6-turn window
    are condensed so memory continuously incorporates newly displaced turns.
    """
    messages = state.get("recent_messages", [])
    running_summary = state.get("running_summary", "")
    covered_topics = list(state.get("covered_topics", []))
    current_topic = state.get("current_topic", "")
    topic_statuses = dict(state.get("topic_statuses", {}))

    if current_topic:
        if current_topic not in covered_topics:
            covered_topics.append(current_topic)
        if current_topic not in topic_statuses:
            topic_statuses[current_topic] = "in_progress"

    # Bound recent messages to last MAX_RECENT_TURNS
    if len(messages) > MAX_RECENT_TURNS:
        bounded_messages = messages[-MAX_RECENT_TURNS:]
        displaced_messages = messages[:-MAX_RECENT_TURNS]

        # Continuously condense displaced messages into the rolling summary
        displaced_claims = [
            m.get("content", "").strip()
            for m in displaced_messages
            if m.get("role") == "user" and m.get("content")
        ]
        displaced_topics = [
            t for t, status in topic_statuses.items() if status in ("assessed", "in_progress")
        ]

        summary_parts = []
        if displaced_topics:
            summary_parts.append(f"Covered topics: {', '.join(displaced_topics)}.")
        if displaced_claims:
            # Capture concise excerpts from displaced candidate claims
            concise_claims = [c[:120] + "..." if len(c) > 120 else c for c in displaced_claims[-3:]]
            summary_parts.append(f"Earlier candidate claims: {' | '.join(concise_claims)}.")

        running_summary = " ".join(summary_parts)
    else:
        bounded_messages = messages

    return {
        "recent_messages": bounded_messages,
        "running_summary": running_summary,
        "covered_topics": covered_topics,
        "topic_statuses": topic_statuses,
    }

async def assess_candidate_turn_node(
    state: InterviewAgentState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
    """
    Evaluates candidate's latest response and deterministically decides next action
    using explicit topic lifecycle states (not_started, in_progress, needs_follow_up, assessed)
    and eliminates legacy keyword heuristics.
    """
    turn_count = state.get("turn_count", 0)
    max_turns = state.get("max_turns", 8)
    latest_answer = state.get("latest_candidate_answer", "").strip()
    current_difficulty = state.get("difficulty", "intermediate")
    current_topic = state.get("current_topic", "")
    domain_skills = state.get("domain_skills", [])
    covered_topics = list(state.get("covered_topics", []))
    topic_statuses = dict(state.get("topic_statuses", {}))
    pending_follow_up = state.get("pending_follow_up", False)
    candidate_evidence = list(state.get("candidate_evidence", []))
    latest_message_id = state.get("latest_candidate_message_id")

    # Check maximum turn limit budget
    if turn_count >= max_turns:
        topic_statuses[current_topic] = "assessed"
        return {
            "next_action": "wrapup",
            "decision_reason": f"Maximum question budget ({max_turns} turns) reached.",
            "pending_follow_up": False,
            "topic_statuses": topic_statuses,
        }

    # Attempt structured decision via model client if available in config
    cfg = config or {}
    model = cfg.get("configurable", {}).get("model")
    decision: Optional[AdaptiveDecision] = None

    if model and hasattr(model, "with_structured_output"):
        try:
            structured_evaluator = model.with_structured_output(AdaptiveDecision)
            remaining_topics = [s for s in domain_skills if topic_statuses.get(s) != "assessed" and s != current_topic]
            eval_prompt = (
                f"Candidate Answer: '{latest_answer}'\n"
                f"Current Topic: {current_topic} (Status: {topic_statuses.get(current_topic, 'in_progress')})\n"
                f"Current Difficulty: {current_difficulty}\n"
                f"Was Previous Question Follow-up: {pending_follow_up}\n"
                f"Remaining Topics: {remaining_topics}\n"
                "Evaluate candidate depth. If candidate made an unverified claim or gave an incomplete answer, "
                "set action='ask_follow_up' and topic_status='needs_follow_up'. "
                "If topic has been adequately assessed, set action='next_topic' and topic_status='assessed'. "
                "If candidate showed exceptional mastery, consider action='increase_difficulty'. "
                "If candidate struggled significantly, consider action='decrease_difficulty'."
            )
            decision = await structured_evaluator.ainvoke([HumanMessage(content=eval_prompt)])
        except Exception as e:
            logger.info(f"Model structured evaluation skipped, using state-driven rules: {e}")

    # State-driven deterministic lifecycle fallback (No keyword heuristics)
    if not decision:
        words = latest_answer.split()
        word_count = len(words)

        if pending_follow_up:
            # Candidate just answered a follow-up probe; resolve the topic
            topic_statuses[current_topic] = "assessed"
            unassessed = [s for s in domain_skills if topic_statuses.get(s) != "assessed"]
            if unassessed:
                action = "next_topic"
                reason = f"Completed follow-up exploration on '{current_topic}'. Advancing to next competency."
                difficulty_delta = 0
                topic_status = "assessed"
            elif turn_count >= max_turns - 1:
                action = "wrapup"
                reason = "All domain competencies explored."
                difficulty_delta = 0
                topic_status = "assessed"
            else:
                action = "increase_difficulty"
                reason = f"Competency '{current_topic}' assessed. Probing edge cases at increased difficulty."
                difficulty_delta = 1
                topic_status = "assessed"
        else:
            # First answer on this topic
            if word_count < 25:
                # Abbreviated answer lacks depth; probe for specifics
                action = "ask_follow_up"
                reason = f"Candidate response on '{current_topic}' is brief ({word_count} words). Probing concrete implementation trade-offs."
                difficulty_delta = 0
                topic_status = "needs_follow_up"
            else:
                # Substantive initial answer; probe failure modes or transition
                unassessed = [s for s in domain_skills if topic_statuses.get(s) not in ("assessed", "in_progress") and s != current_topic]
                if unassessed and turn_count % 2 == 1:
                    # Alternate between follow-up and next topic progression
                    action = "ask_follow_up"
                    reason = f"Probing trade-offs and edge-case handling for '{current_topic}'."
                    difficulty_delta = 0
                    topic_status = "needs_follow_up"
                elif unassessed:
                    action = "next_topic"
                    reason = f"Candidate provided thorough initial analysis on '{current_topic}'. Moving to '{unassessed[0]}'."
                    difficulty_delta = 0
                    topic_status = "assessed"
                else:
                    action = "ask_follow_up"
                    reason = f"Probing edge cases and failure modes on '{current_topic}'."
                    difficulty_delta = 0
                    topic_status = "needs_follow_up"

        extracted_claim = latest_answer[:140] if latest_answer else None
        decision = AdaptiveDecision(
            action=action,
            reason=reason,
            difficulty_delta=difficulty_delta,
            identified_evidence=extracted_claim,
            topic_status=topic_status,
        )

    # Apply topic status update
    if decision.topic_status:
        topic_statuses[current_topic] = decision.topic_status
    elif decision.action == "ask_follow_up":
        topic_statuses[current_topic] = "needs_follow_up"
    elif decision.action == "next_topic":
        topic_statuses[current_topic] = "assessed"

    # Track structured candidate claim linked to transcript message ID
    claim_text = decision.identified_evidence or (latest_answer[:140] if latest_answer else "")
    if claim_text:
        candidate_evidence.append({
            "claim": claim_text,
            "topic": current_topic,
            "message_id": latest_message_id,
            "turn": turn_count,
            "verification_status": "probed" if decision.action == "ask_follow_up" else "unverified",
        })

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
        if decision.suggested_topic and decision.suggested_topic in domain_skills:
            new_topic = decision.suggested_topic
        else:
            remaining = [s for s in domain_skills if topic_statuses.get(s) != "assessed"]
            new_topic = remaining[0] if remaining else (domain_skills[0] if domain_skills else current_topic)

        topic_statuses[new_topic] = "in_progress"
        if new_topic not in covered_topics:
            covered_topics.append(new_topic)

    return {
        "next_action": decision.action,
        "decision_reason": decision.reason,
        "difficulty": new_difficulty,
        "current_topic": new_topic,
        "covered_topics": covered_topics,
        "topic_statuses": topic_statuses,
        "pending_follow_up": decision.action == "ask_follow_up",
        "candidate_evidence": candidate_evidence,
    }

async def generate_question_node(
    state: InterviewAgentState, config: Optional[RunnableConfig] = None
) -> Dict[str, Any]:
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

    if "Candidate Code Submission" in latest_answer or "Execution Status:" in latest_answer:
        instruction = (
            f"The candidate submitted their code solution. Execution details:\n{latest_answer}\n"
            "Analyze their code and test outcomes. If tests passed, ask about time and space complexity (Big-O) or memory trade-offs. "
            "If tests failed, timed out, or threw compilation/runtime errors, ask them what invariant was violated and how they would debug it. "
            "Ask exactly ONE direct question. Under 3 sentences. No praise."
        )
    elif next_action == "ask_follow_up":
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
