import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from langchain_core.messages import SystemMessage, HumanMessage
from backend.app.database.models import Interview, InterviewMessage, Resume, JobDescription
from backend.app.interviews.agent.graph import create_interview_graph
from backend.app.interviews.agent.checkpoint import get_interview_checkpointer
from backend.app.interviews.agent.state import InterviewAgentState
from backend.app.interviews.prompts import build_interviewer_system_prompt
from backend.app.providers.model_client_factory import ModelClientFactory
from backend.app.core.errors import AppException, EntityNotFoundError, translate_model_error
from backend.app.core.logging import logger
from backend.app.interviews.constants import max_turns_for_duration, count_candidate_answers
from backend.app.interviews.agent.policy import pick_persona, persona_prompt

_COMPANIES = ["google", "uber", "openai", "meta", "amazon", "apple", "netflix", "microsoft", "stripe"]


def detect_company(interview: Interview, jd: Optional[JobDescription] = None) -> Optional[str]:
    """
    Company calibration source, most explicit first: the JD's company, a company mock interview (title written by
    tracks.company_context), then legacy whole-word matches on role/skills for the big names.
    """
    from backend.app.tracks.company_context import company_by_name, company_from_title
    chosen = (getattr(interview, "company_name", None) or "").strip()
    if chosen:  # picked explicitly at setup (or taken from the JD)
        c = company_by_name(chosen)
        return c["name"] if c else chosen
    if jd is not None and getattr(jd, "company", None):
        c = company_by_name(jd.company)
        if c:
            return c["name"]
        for comp in _COMPANIES:
            if re.search(rf"\b{comp}\b", jd.company.lower()):
                return comp.capitalize()
    c = company_from_title(interview.title)
    if c:
        return c["name"]
    blob = f"{interview.target_role or ''} {' '.join(interview.domain_skills or [])}".lower()
    for comp in _COMPANIES:
        if re.search(rf"\b{comp}\b", blob):
            return comp.capitalize()
    return None


def build_full_system_prompt(
    interview: Interview,
    domain_skills: List[str],
    resume: Optional[Resume],
    jd: Optional[JobDescription],
    comp_name: Optional[str],
) -> str:
    prompt = build_interviewer_system_prompt(
        category=interview.category,
        target_role=interview.target_role,
        difficulty=interview.difficulty,
        domain_skills=domain_skills,
        jd_role=jd.extracted_role if jd else None,
        jd_skills=jd.extracted_skills if jd else None,
        jd_requirements=jd.extracted_requirements if jd else None,
        resume_skills=resume.extracted_skills if resume else None,
        resume_projects=resume.projects_context if resume else None,
        resume_text=resume.extracted_text if resume else None,
        company_name=comp_name,
        experience_level=getattr(interview, "experience_level", None) or (getattr(jd, "extracted_experience", None) if jd else None),
    )
    persona = pick_persona(interview.id or "", interview.category, comp_name)
    return prompt + persona_prompt(persona, interview.category, interview.target_duration_minutes or 20)


def _awaiting_candidate_questions(interview: Interview) -> bool:
    last_assistant = next((m for m in reversed(interview.messages) if m.role == "assistant"), None)
    return getattr(last_assistant, "kind", None) == "closing"


def _problem_already_presented(interview: Interview) -> bool:
    return any(
        m.role == "assistant" and ("Here is your question" in (m.content or "") or "\n### " in f"\n{m.content or ''}")
        for m in interview.messages
    )


async def _invoke_model(model, messages):
    try:
        return await model.ainvoke(messages)
    except Exception as e:
        logger.warning(f"Interview opening question failed: {type(e).__name__}: {str(e)[:300]}")
        raise translate_model_error(e) from e


class InterviewAgentService:
    """
    Coordinates stateful interview execution through the LangGraph agent,
    maintains PostgreSQL checkpoints, and manages short-term memory & turn persistence.
    """

    @classmethod
    async def start_interview(
        cls,
        db: AsyncSession,
        user_id: str,
        interview: Interview,
        resume: Optional[Resume] = None,
        jd: Optional[JobDescription] = None,
    ) -> str:
        """
        Initializes graph state, sets explicit topic statuses, and generates the first interview question.
        """
        # Resolve user's configured interviewer model client
        task_type = "coding" if interview.category == "dsa" else "interviewer"
        model = await ModelClientFactory.get_chat_model(db, user_id, task_type=task_type)

        from backend.app.interviews.constants import interview_topics
        domain_skills = interview_topics(interview.category, interview.domain_skills)
        current_topic = domain_skills[0]
        topic_statuses = {
            skill: ("in_progress" if skill == current_topic else "not_started")
            for skill in domain_skills
        }

        comp_name = detect_company(interview, jd)
        system_prompt = build_full_system_prompt(interview, domain_skills, resume, jd, comp_name)

        if interview.category == "dsa":
            persona = pick_persona(interview.id or "", "dsa", comp_name)
            initial_question = (
                f"Hi, I'm {persona['name']}, {persona['title']} on {persona['team']}. "
                + (f"This is a {comp_name}-style coding round. " if comp_name else "")
                + f"Plan for the next "
                f"{interview.target_duration_minutes or 20} minutes: one coding problem, we talk it through, then you can "
                "ask me anything. Before the problem, tell me a bit about yourself and which DSA topics you're strongest "
                "and weakest at."
            )
        elif interview.category == "behavioral":
            comp_label = f" for {comp_name}" if comp_name else ""
            first_q_prompt = (
                f"The candidate is ready for a {interview.difficulty}-level HR / Behavioral round{comp_label} "
                f"for the role of {interview.target_role}. Start as an authentic hiring manager: "
                f"Open like a real interviewer: introduce yourself by name and role in one sentence, give a one-line agenda "
                f"for this {interview.target_duration_minutes or 20}-minute round (a few situations from your past work, then "
                "time for their questions), then ask them to tell you a bit about themselves: their background and the "
                "kind of work they've been doing. Don't ask for a specific story yet. ONE question. Plain spoken English, no flattery."
            )
            prompt_messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=first_q_prompt),
            ]
            response = await _invoke_model(model, prompt_messages)
            raw_content = response.content
            initial_question = ("".join(b.get("text", "") for b in raw_content if isinstance(b, dict) and b.get("type") == "text").strip() or str(raw_content)).strip() if isinstance(raw_content, list) else str(raw_content).strip()
        elif interview.category == "managerial":
            comp_label = f" at {comp_name}" if comp_name else ""
            first_q_prompt = (
                f"The candidate is ready for an engineering leadership / Managerial round{comp_label} "
                f"for the role of {interview.target_role}. Start as a VP of Engineering: "
                f"Open like a real interviewer: introduce yourself by name and role in one sentence, a one-line agenda for "
                f"this {interview.target_duration_minutes or 20}-minute round, then ask them to tell you about themselves: "
                "their current role, the team they work in or lead, and what they're responsible for. ONE question. Plain spoken English, no flattery."
            )
            prompt_messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=first_q_prompt),
            ]
            response = await _invoke_model(model, prompt_messages)
            raw_content = response.content
            initial_question = ("".join(b.get("text", "") for b in raw_content if isinstance(b, dict) and b.get("type") == "text").strip() or str(raw_content)).strip() if isinstance(raw_content, list) else str(raw_content).strip()
        else:
            comp_label = f" ({comp_name})" if comp_name else ""
            first_q_prompt = (
                f"The candidate is ready for a {interview.difficulty}-level {interview.category} interview{comp_label} "
                f"for the role of {interview.target_role}. Start the interview like an authentic senior engineering hiring manager: "
                f"Open like a real interviewer: introduce yourself by name and role in one sentence, a one-line agenda for "
                f"this {interview.target_duration_minutes or 20}-minute round (a couple of technical deep dives, then time "
                "for their questions), then ask them to tell you a bit about "
                "themselves: their background, what they've been building lately, and the tools they use most. Don't "
                "assume any technology. ONE question. Plain spoken English, no flattery."
            )

            prompt_messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=first_q_prompt),
            ]

            response = await _invoke_model(model, prompt_messages)
            raw_content = response.content
            if isinstance(raw_content, list):
                initial_question = "".join(
                    b.get("text", "") for b in raw_content if isinstance(b, dict) and b.get("type") == "text"
                ).strip() or str(raw_content)
            else:
                initial_question = str(raw_content).strip()

        resume_context = None
        if resume:
            parts = []
            if resume.extracted_skills:
                parts.append(f"Skills: {', '.join(resume.extracted_skills[:8])}")
            if resume.projects_context:
                proj_summaries = []
                for p in resume.projects_context[:3]:
                    if isinstance(p, dict):
                        title = p.get("title") or p.get("name") or "Project"
                        tech = p.get("technologies") or p.get("tech") or p.get("description") or ""
                        if isinstance(tech, list):
                            tech = ", ".join(tech)
                        proj_summaries.append(f"{title}: {tech}")
                if proj_summaries:
                    parts.append(f"Projects: {'; '.join(proj_summaries)}")
            resume_context = " | ".join(parts) if parts else None

        jd_context = None
        if jd:
            jd_parts = [f"Role: {jd.extracted_role or jd.title}"]
            if jd.extracted_skills:
                jd_parts.append(f"Skills: {', '.join(jd.extracted_skills[:6])}")
            jd_context = " | ".join(jd_parts)

        # Seed initial graph checkpoint in PostgreSQL
        async with get_interview_checkpointer() as checkpointer:
            graph = create_interview_graph(checkpointer=checkpointer)
            thread_id = f"interview_{interview.id}"
            config = {"configurable": {"thread_id": thread_id, "model": model}}

            initial_state: InterviewAgentState = {
                "interview_id": interview.id,
                "user_id": user_id,
                "category": interview.category,
                "target_role": interview.target_role,
                "difficulty": interview.difficulty,
                "domain_skills": domain_skills,
                "jd_context": jd_context,
                "resume_context": resume_context,
                "current_topic": current_topic,
                "covered_topics": [current_topic],
                "topic_statuses": topic_statuses,
                "pending_follow_up": False,
                "running_summary": "",
                "recent_messages": [{"role": "assistant", "content": initial_question}],
                "candidate_evidence": [],
                "turn_count": 0,
                "max_turns": max_turns_for_duration(interview.target_duration_minutes),
                "next_action": "next_topic",
                "phase": "active",
                "system_prompt": system_prompt,
                "topic_follow_ups": {current_topic: 0},
                "topic_struggles": {},
                "topic_questions": {current_topic: 1},
                "answer_log": [],
                "problem_presented": False,
            }
            # Save checkpoint state via graph update
            try:
                await graph.aupdate_state(config, initial_state)
            except Exception as e:
                logger.warning(f"Checkpointer initial state save notice: {e}")

        # Update interview model with current topic and lifecycle statuses
        interview.current_summary = ""
        interview.covered_topics = [current_topic]
        interview.topic_statuses = topic_statuses

        return initial_question

    @classmethod
    async def process_turn(
        cls,
        db: AsyncSession,
        user_id: str,
        interview: Interview,
        candidate_content: str,
        candidate_message_id: Optional[str] = None,
        client_turn_id: Optional[str] = None,
        resume: Optional[Resume] = None,
        jd: Optional[JobDescription] = None,
    ) -> Dict[str, Any]:
        """
        Executes a stateful turn in the interview graph:
        1. Appends candidate answer.
        2. Assesses candidate response for adaptation (follow-up, topic switch, difficulty adjustment).
        3. Generates the next question or concludes session.
        4. Updates database and checkpoint atomically.
        """
        # Resolve task model client
        task_type = "coding" if interview.category == "dsa" else "interviewer"
        model = await ModelClientFactory.get_chat_model(db, user_id, task_type=task_type)

        thread_id = f"interview_{interview.id}"
        config = {"configurable": {"thread_id": thread_id, "model": model}}

        # Load recent conversational history from database
        # Repeat/clarify exchanges are noise for the model; everything else is context.
        history_dicts = [
            {"role": m.role, "content": m.content}
            for m in interview.messages
            if getattr(m, "kind", "answer") not in ("meta", "repeat")
        ]
        candidate_turns = count_candidate_answers(interview.messages)

        async with get_interview_checkpointer() as checkpointer:
            graph = create_interview_graph(checkpointer=checkpointer)

            # Get latest checkpoint state or fallback to reconstructed state
            prior_state: Dict[str, Any] = {}
            try:
                state_snapshot = await graph.aget_state(config)
                if state_snapshot and state_snapshot.values:
                    prior_state = state_snapshot.values
            except Exception as e:
                logger.info(f"Checkpoint retrieval fallback: {e}")

            turn_count = candidate_turns
            from backend.app.interviews.constants import interview_topics
            domain_skills = interview_topics(interview.category, interview.domain_skills)
            covered_topics = prior_state.get("covered_topics") or interview.covered_topics or []
            current_topic = prior_state.get("current_topic") or (domain_skills[0] if domain_skills else "System Architecture")
            running_summary = prior_state.get("running_summary") or interview.current_summary or ""
            topic_statuses = prior_state.get("topic_statuses") or interview.topic_statuses or {}
            for skill in domain_skills:
                if skill not in topic_statuses:
                    topic_statuses[skill] = "in_progress" if skill == current_topic else "not_started"

            candidate_evidence = prior_state.get("candidate_evidence", [])

            input_state: InterviewAgentState = {
                "interview_id": interview.id,
                "user_id": user_id,
                "category": interview.category,
                "target_role": interview.target_role,
                "difficulty": interview.difficulty,
                "domain_skills": domain_skills,
                "jd_context": prior_state.get("jd_context"),
                "resume_context": prior_state.get("resume_context"),
                "current_topic": current_topic,
                "covered_topics": covered_topics,
                "topic_statuses": topic_statuses,
                "pending_follow_up": prior_state.get("pending_follow_up", False),
                "running_summary": running_summary,
                "recent_messages": history_dicts,
                "candidate_evidence": candidate_evidence,
                "latest_candidate_answer": candidate_content,
                "latest_candidate_message_id": candidate_message_id,
                "client_turn_id": client_turn_id,
                "turn_count": turn_count,
                "max_turns": max_turns_for_duration(interview.target_duration_minutes),
                # The closing phase survives across turns (and lost checkpoints): it's derived from the transcript.
                "phase": "closing" if _awaiting_candidate_questions(interview) else "active",
                "coding_problem_id": interview.coding_problem_id,
                # Older checkpoints predate these keys: rebuild instead of silently dropping context.
                # Behavioural/managerial always rebuild so the scope guard applies to interviews already in progress.
                "system_prompt": (None if interview.category in ("behavioral", "managerial") else prior_state.get("system_prompt"))
                or build_full_system_prompt(interview, domain_skills, resume, jd, detect_company(interview, jd)),
                "topic_follow_ups": prior_state.get("topic_follow_ups") or {},
                "topic_struggles": prior_state.get("topic_struggles") or {},
                "topic_questions": prior_state.get("topic_questions") or {},
                "answer_log": prior_state.get("answer_log") or [],
                "problem_presented": bool(prior_state.get("problem_presented")) or _problem_already_presented(interview),
                "offered_switch": bool(prior_state.get("offered_switch")),
            }

            try:
                result_state = await graph.ainvoke(input_state, config=config)
            except Exception as e:
                # Nodes checkpoint as they complete, so a failure in generate_question would
                # leave assessment state (evidence, topic statuses) for a message the DB is about
                # to roll back. Restore the pre-turn snapshot to keep checkpoint and DB consistent.
                if prior_state:
                    try:
                        await graph.aupdate_state(config, dict(prior_state))
                    except Exception as restore_err:
                        logger.warning(f"Checkpoint restore after failed turn failed: {restore_err}")
                logger.warning(f"Interview turn failed for {interview.id}: {type(e).__name__}: {str(e)[:300]}")
                raise translate_model_error(e) from e

        # Update interview model with summary, topics, and lifecycle statuses
        interview.current_summary = result_state.get("running_summary", "")
        interview.covered_topics = result_state.get("covered_topics", [])
        interview.topic_statuses = result_state.get("topic_statuses", topic_statuses)
        interview.difficulty = result_state.get("difficulty", interview.difficulty)

        is_completed = result_state.get("phase") == "completed" or result_state.get("next_action") == "wrapup"
        if is_completed:
            interview.status = "completed"
            interview.completed_at = datetime.now(timezone.utc)

        return {
            "assistant_content": result_state.get("generated_question"),
            "question_metadata": result_state.get("question_metadata", {}),
            "next_action": result_state.get("next_action"),
            "decision_reason": result_state.get("decision_reason"),
            "is_completed": is_completed,
            "running_summary": interview.current_summary,
            "covered_topics": interview.covered_topics,
            "topic_statuses": interview.topic_statuses,
            "candidate_evidence": result_state.get("candidate_evidence", []),
        }

    @classmethod
    async def get_state_snapshot(
        cls,
        db: AsyncSession,
        user_id: str,
        interview: Interview,
    ) -> Dict[str, Any]:
        """
        Inspects durable LangGraph checkpoint state or database fallback for frontend memory display.
        """
        thread_id = f"interview_{interview.id}"
        config = {"configurable": {"thread_id": thread_id}}

        candidate_turns = count_candidate_answers(interview.messages)
        snapshot_values: Dict[str, Any] = {}

        try:
            async with get_interview_checkpointer() as checkpointer:
                graph = create_interview_graph(checkpointer=checkpointer)
                state_snapshot = await graph.aget_state(config)
                if state_snapshot and state_snapshot.values:
                    snapshot_values = state_snapshot.values
        except Exception as e:
            logger.info(f"Checkpointer state inspection note: {e}")

        current_topic = snapshot_values.get("current_topic") or (interview.domain_skills[0] if interview.domain_skills else "System Architecture")
        covered_topics = snapshot_values.get("covered_topics") or interview.covered_topics or []
        topic_statuses = snapshot_values.get("topic_statuses") or interview.topic_statuses or {}
        running_summary = snapshot_values.get("running_summary") or interview.current_summary or ""
        candidate_evidence = snapshot_values.get("candidate_evidence") or []

        return {
            "interview_id": interview.id,
            "status": interview.status,
            "difficulty": interview.difficulty,
            "current_topic": current_topic,
            "covered_topics": covered_topics,
            "topic_statuses": topic_statuses,
            "running_summary": running_summary,
            "candidate_evidence": candidate_evidence,
            "turn_count": candidate_turns,
            "max_turns": max_turns_for_duration(interview.target_duration_minutes),
        }
