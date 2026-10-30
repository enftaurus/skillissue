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
from backend.app.core.errors import AppException, EntityNotFoundError
from backend.app.core.logging import logger

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

        current_topic = interview.domain_skills[0] if interview.domain_skills else "System Architecture"
        domain_skills = interview.domain_skills or [current_topic]
        topic_statuses = {
            skill: ("in_progress" if skill == current_topic else "not_started")
            for skill in domain_skills
        }

        system_prompt = build_interviewer_system_prompt(
            category=interview.category,
            target_role=interview.target_role,
            difficulty=interview.difficulty,
            domain_skills=domain_skills,
            jd_role=jd.extracted_role if jd else None,
            jd_skills=jd.extracted_skills if jd else None,
            jd_requirements=jd.extracted_requirements if jd else None,
            resume_skills=resume.extracted_skills if resume else None,
            resume_projects=resume.projects_context if resume else None,
        )

        if interview.category == "dsa":
            prob_title = "our competitive coding challenge"
            prob_details = ""
            if interview.coding_problem_id:
                from backend.app.coding.problems import get_problem
                prob = get_problem(interview.coding_problem_id)
                if prob:
                    prob_title = prob.title
                    rating_parts = [c for c in getattr(prob, 'constraints', []) if 'Rating' in c]
                    tag_parts = [c for c in getattr(prob, 'constraints', []) if 'Tag' in c or 'Topic' in c]
                    extra = []
                    if rating_parts:
                        extra.append(rating_parts[0])
                    if tag_parts:
                        extra.append(tag_parts[0])
                    if extra:
                        prob_details = f" ({' | '.join(extra)})"
            initial_question = (
                f"Welcome! Today we'll be tackling an algorithmic coding challenge: {prob_title}{prob_details}. "
                "Take a moment to inspect the problem description, constraints, and standard I/O format in your workspace. "
                "Before writing code, please walk me through your initial thoughts and the algorithmic approach you plan to take."
            )
        else:
            first_q_prompt = (
                f"The candidate is ready for a {interview.difficulty}-level {interview.category} interview "
                f"for the role of {interview.target_role}. Start the interview like an authentic senior engineering hiring manager: "
                "Welcome them and ask them to briefly introduce themselves, their primary tech stack, and an interesting project or architectural challenge they handled recently. "
                "Ask exactly ONE concise question under 3 sentences. No artificial flattery."
            )

            prompt_messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=first_q_prompt),
            ]

            response = await model.ainvoke(prompt_messages)
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
                "max_turns": 8,
                "next_action": "next_topic",
                "phase": "active",
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
        history_dicts = [{"role": m.role, "content": m.content} for m in interview.messages]
        candidate_turns = len([m for m in interview.messages if m.role == "user"])

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
            domain_skills = interview.domain_skills or ["System Architecture"]
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
                "max_turns": 8,
                "phase": "active",
            }

            result_state = await graph.ainvoke(input_state, config=config)

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

        candidate_turns = len([m for m in interview.messages if m.role == "user"])
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
            "max_turns": 8,
        }
