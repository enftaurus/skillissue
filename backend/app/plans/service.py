from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from backend.app.database.models import Plan, PlanTask, Evaluation, UserProfile
from backend.app.plans.schemas import PlanAdaptRequest
from backend.app.providers.factory import ModelFactory
from backend.app.core.errors import EntityNotFoundError, AppException
from backend.app.core.logging import logger

class PlanService:
    @classmethod
    async def create_plan_from_evaluation(
        cls,
        db: AsyncSession,
        user_id: str,
        evaluation_id: str,
    ) -> Plan:
        # Load evaluation
        eval_res = await db.execute(
            select(Evaluation).where(Evaluation.id == evaluation_id, Evaluation.user_id == user_id)
        )
        evaluation = eval_res.scalar_one_or_none()
        if not evaluation:
            raise EntityNotFoundError("Evaluation", evaluation_id)

        # Archive any existing active plans for this user
        existing_active = await db.execute(
            select(Plan).where(Plan.user_id == user_id, Plan.status == "active")
        )
        for old_plan in existing_active.scalars().all():
            old_plan.status = "archived"

        # Load user profile for daily study minutes
        prof_res = await db.execute(select(UserProfile).where(UserProfile.user_id == user_id))
        profile = prof_res.scalar_one_or_none()
        daily_minutes = profile.daily_study_minutes if profile else 45
        target_role = profile.target_role if profile else "Software Engineer"

        # Prompt model to generate personalized multi-day plan
        provider = await ModelFactory.get_for_user(db, user_id, task_type="general")
        prompt = (
            f"Generate a customized 7-day technical improvement roadmap (Planly) for a {target_role}.\n"
            f"Daily study availability: {daily_minutes} minutes/day.\n"
            f"Demonstrated Weaknesses:\n- " + "\n- ".join(evaluation.weaknesses[:4]) + "\n"
            f"Missing Concepts:\n- " + "\n- ".join(evaluation.missing_concepts[:4]) + "\n\n"
            "Format your response as structured JSON conforming to this schema:\n"
            '{\n'
            '  "title": "7-Day Targeted Systems Mastery Plan",\n'
            '  "target_skills": ["Caching", "Database Indexing", ...],\n'
            '  "tasks": [\n'
            '    {\n'
            '      "day_number": 1,\n'
            '      "title": "...",\n'
            '      "description": "...",\n'
            '      "task_type": "concept",\n'  # concept, practice, coding, reassessment
            f'      "estimated_minutes": {daily_minutes},\n'
            '      "external_resources": [{"title": "...", "url": "...", "type": "documentation"}]\n'
            '    }\n'
            '  ]\n'
            '}'
        )
        system_prompt = "You are a lead engineering mentor designing high-yield, bite-sized daily practice routines to eliminate interview weaknesses."

        response = await provider.generate_json(prompt=prompt, system_prompt=system_prompt)
        parsed = response.parsed_json or {}

        title = parsed.get("title") or "7-Day Technical Improvement Roadmap"
        target_skills = parsed.get("target_skills") or ["Database Optimization", "System Reliability", "Async Concurrency"]
        tasks_data = parsed.get("tasks", [])

        plan = Plan(
            user_id=user_id,
            evaluation_id=evaluation_id,
            title=title,
            target_role=target_role,
            target_skills=target_skills,
            status="active",
            total_days=len(tasks_data) if tasks_data else 7,
            current_day=1,
            daily_study_minutes=daily_minutes,
        )
        db.add(plan)
        await db.flush()

        for idx, t_data in enumerate(tasks_data, start=1):
            task = PlanTask(
                plan_id=plan.id,
                day_number=t_data.get("day_number", idx),
                title=t_data.get("title", f"Day {idx} Practice"),
                description=t_data.get("description", "Review core engineering concepts and complete exercises."),
                task_type=t_data.get("task_type", "practice"),
                estimated_minutes=t_data.get("estimated_minutes", daily_minutes),
                external_resources=t_data.get("external_resources", []),
                is_completed=False,
            )
            db.add(task)

        await db.commit()
        return await cls.get_plan_by_id(db, user_id, plan.id)

    @classmethod
    async def toggle_task_completion(
        cls,
        db: AsyncSession,
        user_id: str,
        task_id: str,
        is_completed: bool,
    ) -> PlanTask:
        result = await db.execute(
            select(PlanTask)
            .join(Plan)
            .where(PlanTask.id == task_id, Plan.user_id == user_id)
        )
        task = result.scalar_one_or_none()
        if not task:
            raise EntityNotFoundError("PlanTask", task_id)

        task.is_completed = is_completed
        task.completed_at = datetime.now(timezone.utc) if is_completed else None

        # Check if plan current_day should advance
        plan_res = await db.execute(
            select(Plan).options(selectinload(Plan.tasks)).where(Plan.id == task.plan_id)
        )
        plan = plan_res.scalar_one_or_none()
        if plan:
            completed_days = [t.day_number for t in plan.tasks if t.is_completed]
            if completed_days:
                max_completed = max(completed_days)
                if max_completed >= plan.current_day and max_completed < plan.total_days:
                    plan.current_day = max_completed + 1

        await db.commit()
        await db.refresh(task)
        return task

    @classmethod
    async def adapt_plan(
        cls,
        db: AsyncSession,
        user_id: str,
        plan_id: str,
        data: PlanAdaptRequest,
    ) -> Plan:
        """
        Adapts the plan when the student misses days or falls behind schedule.
        Re-indexes remaining uncompleted tasks starting from current_day forward,
        retaining reassessment on the final day.
        """
        plan = await cls.get_plan_by_id(db, user_id, plan_id)

        uncompleted_tasks = [t for t in plan.tasks if not t.is_completed]
        if not uncompleted_tasks:
            return plan

        # Shift day numbers of uncompleted tasks forward by days_behind, capping at 14 total days
        days_shift = data.days_behind
        new_total_days = min(14, plan.total_days + days_shift)
        plan.total_days = new_total_days

        start_day = plan.current_day
        for idx, task in enumerate(uncompleted_tasks):
            task.day_number = min(new_total_days, start_day + idx)

        await db.commit()
        return await cls.get_plan_by_id(db, user_id, plan_id)

    @staticmethod
    async def get_active_plan(db: AsyncSession, user_id: str) -> Optional[Plan]:
        result = await db.execute(
            select(Plan)
            .options(selectinload(Plan.tasks))
            .where(Plan.user_id == user_id, Plan.status == "active")
            .order_by(Plan.created_at.desc())
        )
        return result.scalars().first()

    @staticmethod
    async def get_plan_by_id(db: AsyncSession, user_id: str, plan_id: str) -> Plan:
        result = await db.execute(
            select(Plan)
            .options(selectinload(Plan.tasks))
            .where(Plan.id == plan_id, Plan.user_id == user_id)
        )
        plan = result.scalar_one_or_none()
        if not plan:
            raise EntityNotFoundError("Plan", plan_id)
        return plan

    @staticmethod
    async def list_plans(db: AsyncSession, user_id: str) -> List[Plan]:
        result = await db.execute(
            select(Plan)
            .options(selectinload(Plan.tasks))
            .where(Plan.user_id == user_id)
            .order_by(Plan.created_at.desc())
        )
        return list(result.scalars().all())
