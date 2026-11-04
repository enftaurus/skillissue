import re
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

    if turn_count > 1:
        # Optimized lean system prompt for conversational turns — saves >70% tokens while preserving Gilfoyle rigor
        system_prompt = (
            f"You are the technical interviewer for a {difficulty} {target_role} ({category.upper()} interview). "
            f"Current Topic: {current_topic}. "
            "Persona: Senior Staff Engineer / Hiring Manager. Direct, sharp, politely skeptical, zero praise. "
            "Ask exactly ONE concise question (1 to 3 sentences). Probe trade-offs, edge cases, failure scenarios, and concrete metrics. "
            "Never ask compound questions."
        )
        if running_summary:
            system_prompt += f"\nPrevious Context: {running_summary[:250]}"
    else:
        system_prompt = build_interviewer_system_prompt(
            category=category,
            target_role=target_role,
            difficulty=difficulty,
            domain_skills=domain_skills,
        )
        if running_summary:
            system_prompt += f"\n\nContext from earlier in this interview:\n{running_summary}"
        if state.get("resume_context"):
            system_prompt += f"\n\nCandidate Resume Context:\n{state['resume_context']}"
        if state.get("jd_context"):
            system_prompt += f"\n\nJob Description Context:\n{state['jd_context']}"

    # Build prompt messages
    prompt_messages = [SystemMessage(content=system_prompt)]
    for m in recent_messages:
        if m.get("role") == "user":
            prompt_messages.append(HumanMessage(content=m.get("content", "")))
        elif m.get("role") == "assistant":
            prompt_messages.append(AIMessage(content=m.get("content", "")))

    has_problem_been_presented = any(
        ("### " in m.get("content", "") or "Here is your question" in m.get("content", ""))
        for m in recent_messages if m.get("role") == "assistant"
    )

    if category == "dsa" and not has_problem_been_presented:
        from backend.app.coding.problems import get_problem
        prob_id = state.get("coding_problem_id") or "two-sum"
        prob = get_problem(prob_id)
        if prob:
            sample_io_parts = []
            if getattr(prob, "sample_test_cases", None):
                for idx, sc in enumerate(prob.sample_test_cases, 1):
                    sample_io_parts.append(
                        f"**Sample {idx} Input:**\n```\n{sc.get('stdin', '').strip()}\n```\n"
                        f"**Sample {idx} Output:**\n```\n{sc.get('expected_stdout', '').strip()}\n```"
                    )
            samples_str = "\n\n".join(sample_io_parts)
            constraints_str = "\n".join(f"- {c}" for c in getattr(prob, "constraints", []))

            prob_spec = (
                f"### {prob.title}\n\n"
                f"{prob.description}\n\n"
                f"**Input Format:**\n{prob.input_format}\n\n"
                f"**Output Format:**\n{prob.output_format}\n\n"
                f"**Constraints:**\n{constraints_str}\n\n"
                f"{samples_str}"
            )
        else:
            prob_spec = "### Algorithmic Challenge\nSolve the given challenge satisfying standard constraints."

        instruction = (
            f"The candidate just introduced themselves: '{latest_answer}'.\n\n"
            "Respond in the authentic Skill Issue persona (direct, witty, sharp, Gilfoyle-level engineering precision, zero fake flattery):\n"
            "1. Briefly acknowledge their introduction and favorite DSA topic with authentic technical wit (e.g. if they mentioned DP, overlapping subproblems, competitive programming, graphs, trees, etc., make a sharp 1-2 sentence remark).\n"
            "2. Transition: 'Now let\\'s start today\\'s session. Here is your question:'\n"
            f"3. Present the FULL problem title and detailed problem description:\n\n{prob_spec}\n\n"
            "4. Ask them: 'Before you start writing code, please walk me through your initial thoughts and the algorithmic approach you plan to follow, your target time and space complexity, and any edge cases you\\'re considering.'"
        )
    elif "Candidate Code Submission" in latest_answer or "Execution Status:" in latest_answer:
        # Detect if code is quadratic brute force (nested loops without hash lookup)
        code_match = re.search(r"```(?:\w+)?\n([\s\S]*?)```", latest_answer)
        code_snippet = code_match.group(1) if code_match else latest_answer
        clean_lines = [l.strip() for l in code_snippet.split("\n") if l.strip() and not l.strip().startswith(("#", "//", "/*", "*"))]
        clean_text = "\n".join(clean_lines).lower()
        has_nested_loop = bool(re.search(r'for\s+.*\n\s+.*for\s+', clean_text)) or bool(re.search(r'while\s+.*\n\s+.*(while|for)\s+', clean_text))
        has_hash_map = bool(re.search(r'\b(dict|set|\{\}|hashmap|hashset|unordered_map|unordered_set|seen|lookup)\b', clean_text))
        has_two_pointers = bool(re.search(r'\b(left|right|start|end|ptr|low|high)\b', clean_text) and re.search(r'(\+= 1|-= 1|\+\+|--)', clean_text))
        is_brute_force = has_nested_loop and not (has_hash_map or has_two_pointers)

        if is_brute_force:
            instruction = (
                f"The candidate executed their code solution. Execution outcome:\n{latest_answer}\n\n"
                "CRITICAL INTERVIEWER TASK — BRUTE FORCE DETECTED:\n"
                "1. Acknowledge that the brute-force baseline functionally passes basic sample cases, but state directly that the nested loop O(N^2) quadratic time complexity will hit a Time Limit Exceeded (TLE) bottleneck at scale (N >= 10^5).\n"
                "2. Provide a Socratic, progressive hint towards the optimal approach (e.g. trading space for time using a hash map to look up previously seen elements in O(1) time). Do NOT write out the whole solution code.\n"
                "3. Ask them: 'What is the exact time and space complexity of your current solution, and how would you refactor this repeated scanning logic to achieve an optimal O(N) time complexity?'\n"
                "Persona: Gilfoyle-level engineering rigor, direct, under 4 sentences, zero artificial flattery."
            )
        else:
            instruction = (
                f"The candidate executed their code solution. Execution outcome:\n{latest_answer}\n\n"
                "CRITICAL INTERVIEWER TASK — COMPLEXITY & BOUNDARY ANALYSIS:\n"
                "If tests passed: Inquire about the exact time and space complexity (Big-O) trade-offs, and challenge them on tricky edge cases (e.g. duplicate values, empty or extreme inputs, integer overflow).\n"
                "If tests failed or timed out: Ask what invariant failed and how they would systematically debug it.\n"
                "Persona: Gilfoyle-level engineering rigor, direct, under 3 sentences, zero artificial flattery."
            )
    elif category == "behavioral":
        if next_action == "ask_follow_up":
            instruction = (
                f"The candidate said: '{latest_answer}'. "
                "Probe using the STAR method: ask for their specific individual contribution, the concrete metrics/results, or what trade-off was made. "
                "Ask exactly ONE direct follow-up question. Under 3 sentences. No praise."
            )
        else:
            instruction = (
                f"Move to a new behavioral scenario on '{current_topic}'. "
                "Ask a situational or experiential question regarding technical disagreement, ownership during a critical outage, or navigating ambiguous requirements. "
                "Ask exactly ONE direct question. Under 3 sentences. No praise."
            )
    elif category == "managerial":
        if next_action == "ask_follow_up":
            instruction = (
                f"The candidate said: '{latest_answer}'. "
                "Probe their engineering leadership decision: ask how they measured team impact, handled stakeholder pushback, or mitigated technical risk. "
                "Ask exactly ONE direct question. Under 3 sentences. No praise."
            )
        else:
            instruction = (
                f"Move to a leadership/management topic on '{current_topic}'. "
                "Ask a question regarding prioritization between technical debt refactoring versus product roadmap deadlines, or mentoring a struggling engineer. "
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
    raw_content = response.content
    if isinstance(raw_content, list):
        question_text = "".join(
            b.get("text", "") for b in raw_content if isinstance(b, dict) and b.get("type") == "text"
        ).strip() or str(raw_content)
    else:
        question_text = str(raw_content).strip()

    # Strip embedded <think> tags if present
    cleaned_q = re.sub(r"<think>[\s\S]*?</think>", "", question_text, flags=re.DOTALL).strip()
    cleaned_q = re.sub(r"^[\s\S]*?</think>", "", cleaned_q, flags=re.DOTALL).strip()
    if cleaned_q:
        question_text = cleaned_q

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
