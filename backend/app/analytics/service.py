from collections import Counter
from datetime import datetime
from typing import Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from backend.app.database.models import Interview, Evaluation, Plan, PlanTask, UserSkill
from backend.app.analytics.schemas import (
    AnalyticsDashboardResponse, ScoreHistoryPoint, DimensionTrend, ReassessmentComparison,
    UserSkillResponse
)
from backend.app.interviews.rubrics import get_rubric_for_category

class AnalyticsService:
    @staticmethod
    async def get_dashboard(db: AsyncSession, user_id: str) -> AnalyticsDashboardResponse:
        # 1. Fetch all interviews with evaluations
        int_res = await db.execute(
            select(Interview)
            .options(selectinload(Interview.ai_evaluation))
            .where(Interview.user_id == user_id)
            .order_by(Interview.created_at.asc())
        )
        interviews = list(int_res.scalars().all())

        total_interviews = len(interviews)
        completed_interviews = len([i for i in interviews if i.status == "completed"])

        evaluations_with_interview = [
            (i, i.ai_evaluation) for i in interviews if i.ai_evaluation is not None
        ]

        # Score history
        score_history: List[ScoreHistoryPoint] = []
        scores: List[float] = []
        strengths_counter: Counter = Counter()
        weaknesses_counter: Counter = Counter()
        dim_scores_map: Dict[str, List[float]] = {}

        for intv, ev in evaluations_with_interview:
            scores.append(ev.overall_score)
            score_history.append(
                ScoreHistoryPoint(
                    interview_id=intv.id,
                    title=intv.title,
                    category=intv.category,
                    mode=intv.mode,
                    overall_score=ev.overall_score,
                    completed_at=ev.created_at,
                )
            )

            for s in ev.strengths:
                strengths_counter[s] += 1
            for w in ev.weaknesses:
                weaknesses_counter[w] += 1

            for dim_id, data in ev.rubric_dimension_scores.items():
                if isinstance(data, dict) and "score" in data:
                    dim_scores_map.setdefault(dim_id, []).append(float(data["score"]))

        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0

        # Dimension trends
        dim_trends: List[DimensionTrend] = []
        for dim_id, val_list in dim_scores_map.items():
            dim_name = dim_id.replace("_", " ").title()
            dim_trends.append(
                DimensionTrend(
                    dimension_id=dim_id,
                    dimension_name=dim_name,
                    scores=val_list,
                    latest_score=val_list[-1],
                    average_score=round(sum(val_list) / len(val_list), 1),
                )
            )

        # Reassessment comparisons (compare interviews with the exact same category)
        reassessments: List[ReassessmentComparison] = []
        category_interviews: Dict[str, List[tuple[Interview, Evaluation]]] = {}
        for intv, ev in evaluations_with_interview:
            category_interviews.setdefault(intv.category, []).append((intv, ev))

        for cat, pair_list in category_interviews.items():
            if len(pair_list) >= 2:
                # Compare first attempt with latest attempt
                baseline_int, baseline_ev = pair_list[0]
                latest_int, latest_ev = pair_list[-1]

                delta = round(latest_ev.overall_score - baseline_ev.overall_score, 1)

                improved_dims = []
                stable_dims = []
                declined_dims = []

                b_dims = baseline_ev.rubric_dimension_scores or {}
                l_dims = latest_ev.rubric_dimension_scores or {}

                rubric_dims = {d.id: d.name for d in get_rubric_for_category(cat)}

                for dim_id, dim_meta in b_dims.items():
                    if dim_id in l_dims:
                        b_score = b_dims[dim_id].get("score", 0)
                        l_score = l_dims[dim_id].get("score", 0)
                        dim_title = rubric_dims.get(dim_id, dim_id.replace("_", " ").title())
                        if l_score > b_score:
                            improved_dims.append(f"{dim_title} (+{l_score - b_score})")
                        elif l_score == b_score:
                            stable_dims.append(f"{dim_title} ({l_score}/5)")
                        else:
                            declined_dims.append(f"{dim_title} ({l_score - b_score})")

                reassessments.append(
                    ReassessmentComparison(
                        baseline_interview_id=baseline_int.id,
                        baseline_title=baseline_int.title,
                        baseline_date=baseline_ev.created_at,
                        baseline_score=baseline_ev.overall_score,
                        reassessment_interview_id=latest_int.id,
                        reassessment_title=latest_int.title,
                        reassessment_date=latest_ev.created_at,
                        reassessment_score=latest_ev.overall_score,
                        score_delta=delta,
                        category=cat,
                        is_comparable=True,
                        improved_dimensions=improved_dims,
                        stable_dimensions=stable_dims,
                        declined_dimensions=declined_dims,
                    )
                )

        # Planly task metrics
        plan_res = await db.execute(
            select(PlanTask).join(Plan).where(Plan.user_id == user_id)
        )
        all_tasks = list(plan_res.scalars().all())
        total_tasks = len(all_tasks)
        completed_tasks = len([t for t in all_tasks if t.is_completed])
        completion_rate = round((completed_tasks / total_tasks * 100), 1) if total_tasks > 0 else 0.0

        recurring_strengths = [s for s, count in strengths_counter.most_common(5)]
        recurring_weaknesses = [w for w, count in weaknesses_counter.most_common(5)]

        # Fetch persistent user skill map
        skills_res = await db.execute(
            select(UserSkill).where(UserSkill.user_id == user_id).order_by(UserSkill.score.desc())
        )
        skills = list(skills_res.scalars().all())
        skill_responses = [UserSkillResponse.model_validate(s) for s in skills]

        return AnalyticsDashboardResponse(
            total_interviews=total_interviews,
            completed_interviews=completed_interviews,
            average_overall_score=avg_score,
            plan_tasks_completed=completed_tasks,
            plan_tasks_total=total_tasks,
            planly_completion_rate=completion_rate,
            score_history=score_history,
            dimension_trends=dim_trends,
            recurring_strengths=recurring_strengths,
            recurring_weaknesses=recurring_weaknesses,
            reassessments=reassessments,
            skills=skill_responses,
        )

    @staticmethod
    async def get_skills(db: AsyncSession, user_id: str) -> List[UserSkill]:
        res = await db.execute(
            select(UserSkill).where(UserSkill.user_id == user_id).order_by(UserSkill.score.desc())
        )
        return list(res.scalars().all())
