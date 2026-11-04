from datetime import datetime, timezone
from typing import List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.core.errors import EntityNotFoundError, AppException
from backend.app.database.models import CompanyTrack, CompanyProblem, UserCompanyProgress
from backend.app.tracks.schemas import (
    CompanyTrackSummary, CompanyTrackDetail, CompanyProblemSummary, CompanyProblemDetail,
    SolveCompanyProblemResponse, PresetSimulationResponse, ToggleProblemSolvedResponse
)
from backend.app.tracks.seed_data import TRACKS_SEED_DATA
from backend.app.tracks.company_registry import CompanyRegistry
from backend.app.tracks.csv_loader import load_company_problems_from_csv


class CompanyTrackService:
    @classmethod
    async def seed_tracks_if_empty(cls, db: AsyncSession) -> None:
        existing_res = await db.execute(select(CompanyTrack.slug))
        existing_slugs = {s.lower() for s in existing_res.scalars().all()}

        # 1. Seed TRACKS_SEED_DATA if missing
        for track_data in TRACKS_SEED_DATA:
            slug = track_data["slug"].lower()
            if slug in existing_slugs:
                continue
            problems_data = track_data.get("problems", [])
            track = CompanyTrack(
                name=track_data["name"],
                slug=slug,
                tier=track_data.get("tier", "gold"),
                role_title=track_data.get("role_title", "Software Development Engineer"),
                description=track_data.get("description", ""),
                community_tips=track_data.get("community_tips", []),
                total_problems=len(problems_data),
                initial_unlocked_count=3,
                logo_icon=track_data.get("logo_icon", "Building2")
            )
            db.add(track)
            await db.flush()
            existing_slugs.add(slug)

            for p_data in problems_data:
                problem = CompanyProblem(
                    company_track_id=track.id,
                    title=p_data["title"],
                    slug=p_data["slug"],
                    difficulty=p_data.get("difficulty", "MEDIUM"),
                    frequency_score=float(p_data.get("frequency_score", 100.0)),
                    acceptance_rate=float(p_data.get("acceptance_rate", 0.5)),
                    topics=p_data.get("topics", []),
                    order_index=int(p_data.get("order_index", 1)),
                    is_initially_unlocked=bool(p_data.get("is_initially_unlocked", False)),
                    description=p_data.get("description", f"Solve on LeetCode: https://leetcode.com/problems/{p_data['slug']}/"),
                    starter_code=p_data.get("starter_code", {}),
                    test_cases=p_data.get("test_cases", [])
                )
                db.add(problem)

        # 2. Seed remaining companies from COMPANIES_50
        for comp in CompanyRegistry.get_all_companies():
            slug = comp["slug"].lower()
            if slug in existing_slugs:
                continue
            probs = comp.get("problems", [])
            track = CompanyTrack(
                name=comp["name"],
                slug=slug,
                tier=comp.get("tier", "silver"),
                role_title=comp.get("role_title", "Software Development Engineer"),
                description=comp.get("description", ""),
                community_tips=comp.get("community_tips", []),
                total_problems=len(probs),
                initial_unlocked_count=3,
                logo_icon=comp.get("logo_icon", "Building2")
            )
            db.add(track)
            await db.flush()
            existing_slugs.add(slug)

            for p_data in probs:
                problem = CompanyProblem(
                    company_track_id=track.id,
                    title=p_data["title"],
                    slug=p_data["slug"],
                    difficulty=p_data.get("difficulty", "MEDIUM"),
                    frequency_score=float(p_data.get("frequency", 90.0)),
                    acceptance_rate=0.45,
                    topics=p_data.get("topics", []),
                    order_index=int(p_data.get("order", 1)),
                    is_initially_unlocked=bool(p_data.get("is_unlocked", p_data.get("order", 1) <= 3)),
                    description=f"Solve on LeetCode: https://leetcode.com/problems/{p_data['slug']}/",
                    starter_code={"python": f"# LeetCode: https://leetcode.com/problems/{p_data['slug']}/\n"},
                    test_cases=[]
                )
                db.add(problem)

        await db.commit()

    @classmethod
    async def get_or_create_user_progress(
        cls, db: AsyncSession, user_id: str, track_id: str
    ) -> UserCompanyProgress:
        result = await db.execute(
            select(UserCompanyProgress).where(
                UserCompanyProgress.user_id == user_id,
                UserCompanyProgress.company_track_id == track_id
            )
        )
        progress = result.scalar_one_or_none()
        if not progress:
            progress = UserCompanyProgress(
                user_id=user_id,
                company_track_id=track_id,
                unlocked_count=3,
                solved_count=0,
                solved_problem_ids=[]
            )
            db.add(progress)
            await db.flush()
        return progress

    @classmethod
    async def get_all_tracks(cls, db: AsyncSession, user_id: str) -> List[CompanyTrackSummary]:
        await cls.seed_tracks_if_empty(db)

        result = await db.execute(
            select(CompanyTrack).order_by(
                CompanyTrack.tier == "gold",
                CompanyTrack.tier == "silver",
                CompanyTrack.name
            )
        )
        tracks = list(result.scalars().all())

        summaries: List[CompanyTrackSummary] = []
        existing_slugs = set()
        for track in tracks:
            existing_slugs.add(track.slug.lower())
            progress = await cls.get_or_create_user_progress(db, user_id, track.id)
            csv_probs = load_company_problems_from_csv(track.slug)
            total_cnt = len(csv_probs) if csv_probs else track.total_problems
            unlocked = max(track.initial_unlocked_count, progress.unlocked_count)
            summaries.append(
                CompanyTrackSummary(
                    id=track.id,
                    name=track.name,
                    slug=track.slug,
                    tier=track.tier,
                    role_title=track.role_title,
                    description=track.description,
                    community_tips=track.community_tips or [],
                    total_problems=total_cnt,
                    unlocked_count=min(total_cnt, unlocked),
                    solved_count=progress.solved_count,
                    logo_icon=track.logo_icon,
                    is_gold_mine=(track.tier == "gold")
                )
            )

        # Merge dynamic 50+ companies from registry
        for comp in CompanyRegistry.get_all_companies():
            if comp["slug"].lower() not in existing_slugs:
                csv_probs = load_company_problems_from_csv(comp["slug"])
                probs = csv_probs if csv_probs else comp.get("problems", [])
                total_cnt = len(probs)
                unlocked_cnt = min(total_cnt, 3)
                summaries.append(
                    CompanyTrackSummary(
                        id=f"reg-{comp['slug']}",
                        name=comp["name"],
                        slug=comp["slug"],
                        tier=comp.get("tier", "silver"),
                        role_title=comp.get("role_title", "Software Development Engineer"),
                        description=comp.get("description", ""),
                        community_tips=comp.get("community_tips", []),
                        total_problems=total_cnt,
                        unlocked_count=unlocked_cnt,
                        solved_count=0,
                        logo_icon=comp.get("logo_icon", "Building2"),
                        is_gold_mine=(comp.get("tier") == "gold")
                    )
                )

        await db.commit()
        return summaries

    @classmethod
    async def get_track_by_slug(
        cls, db: AsyncSession, user_id: str, slug: str
    ) -> CompanyTrackDetail:
        await cls.seed_tracks_if_empty(db)

        result = await db.execute(
            select(CompanyTrack)
            .options(selectinload(CompanyTrack.problems))
            .where(CompanyTrack.slug == slug)
        )
        track = result.scalar_one_or_none()

        # If track not in DB yet, auto-create it from registry so progress is persisted
        if not track:
            comp_reg = CompanyRegistry.get_company_by_slug(slug)
            name = comp_reg["name"] if comp_reg else slug.replace("-", " ").title()
            tier = comp_reg.get("tier", "silver") if comp_reg else "silver"
            role_title = comp_reg.get("role_title", "Software Development Engineer") if comp_reg else "Software Development Engineer"
            desc = comp_reg.get("description", "") if comp_reg else ""
            tips = comp_reg.get("community_tips", []) if comp_reg else []
            logo = comp_reg.get("logo_icon", "Building2") if comp_reg else "Building2"

            track = CompanyTrack(
                name=name,
                slug=slug,
                tier=tier,
                role_title=role_title,
                description=desc,
                community_tips=tips,
                total_problems=100,
                initial_unlocked_count=3,
                logo_icon=logo,
            )
            db.add(track)
            await db.flush()

        progress = await cls.get_or_create_user_progress(db, user_id, track.id)
        effective_unlocked = max(track.initial_unlocked_count, progress.unlocked_count)
        solved_ids = set(progress.solved_problem_ids or [])

        # Priority: Load real LeetCode questions directly from repository CSV (5. All.csv)
        csv_probs = load_company_problems_from_csv(slug)
        if csv_probs:
            problem_summaries = []
            for p in csv_probs:
                p_id = f"p-{slug}-{p['order_index']}"
                is_unlocked = p["order_index"] <= effective_unlocked
                is_solved = (p_id in solved_ids) or (p["slug"] in solved_ids)
                problem_summaries.append(
                    CompanyProblemSummary(
                        id=p_id,
                        title=p["title"],
                        slug=p["slug"],
                        leetcode_url=p["leetcode_url"],
                        difficulty=p["difficulty"],
                        frequency_score=p["frequency_score"],
                        acceptance_rate=p["acceptance_rate"],
                        topics=p["topics"],
                        order_index=p["order_index"],
                        is_unlocked=is_unlocked,
                        is_solved=is_solved
                    )
                )
            total_cnt = len(csv_probs)
        else:
            sorted_problems = sorted(track.problems, key=lambda p: p.order_index)
            problem_summaries = []
            for p in sorted_problems:
                is_unlocked = p.order_index <= effective_unlocked
                is_solved = p.id in solved_ids
                problem_summaries.append(
                    CompanyProblemSummary(
                        id=p.id,
                        title=p.title,
                        slug=p.slug,
                        leetcode_url=f"https://leetcode.com/problems/{p.slug}/",
                        difficulty=p.difficulty,
                        frequency_score=p.frequency_score,
                        acceptance_rate=p.acceptance_rate,
                        topics=p.topics or [],
                        order_index=p.order_index,
                        is_unlocked=is_unlocked,
                        is_solved=is_solved
                    )
                )
            total_cnt = track.total_problems

        # Update track.total_problems in DB if count changed
        if track.total_problems != total_cnt:
            track.total_problems = total_cnt

        await db.commit()
        return CompanyTrackDetail(
            id=track.id,
            name=track.name,
            slug=track.slug,
            tier=track.tier,
            role_title=track.role_title,
            description=track.description,
            community_tips=track.community_tips or [],
            total_problems=total_cnt,
            unlocked_count=min(total_cnt, effective_unlocked),
            solved_count=len([p for p in problem_summaries if p.is_solved]),
            logo_icon=track.logo_icon,
            is_gold_mine=(track.tier == "gold"),
            problems=problem_summaries
        )


    @classmethod
    async def get_problem_detail(
        cls, db: AsyncSession, user_id: str, problem_id: str
    ) -> CompanyProblemDetail:
        # 1. Handle dynamic CSV problem IDs: p-{slug}-{order_index}
        if problem_id.startswith("p-") or problem_id.startswith("prob-"):
            parts = problem_id.split("-")
            if len(parts) >= 3 and parts[-1].isdigit():
                slug = "-".join(parts[1:-1])
                order_index = int(parts[-1])
            else:
                slug = parts[1]
                order_index = 1

            track_res = await db.execute(select(CompanyTrack).where(CompanyTrack.slug == slug))
            track = track_res.scalar_one_or_none()
            if not track:
                comp_reg = CompanyRegistry.get_company_by_slug(slug)
                name = comp_reg["name"] if comp_reg else slug.replace("-", " ").title()
                track = CompanyTrack(
                    name=name,
                    slug=slug,
                    tier="silver",
                    role_title="Software Development Engineer",
                    description="",
                    community_tips=[],
                    total_problems=100,
                    initial_unlocked_count=3,
                    logo_icon="Building2",
                )
                db.add(track)
                await db.flush()

            progress = await cls.get_or_create_user_progress(db, user_id, track.id)
            effective_unlocked = max(track.initial_unlocked_count, progress.unlocked_count)
            is_unlocked = order_index <= effective_unlocked
            is_solved = problem_id in (progress.solved_problem_ids or [])

            if not is_unlocked:
                raise AppException(
                    f"This question is locked in the {track.name} Track. Solve earlier questions to unlock.",
                    code="PROBLEM_LOCKED",
                    status_code=403
                )

            csv_probs = load_company_problems_from_csv(slug)
            p = next((x for x in csv_probs if x["order_index"] == order_index), None)
            if not p:
                raise EntityNotFoundError("CompanyProblem", problem_id)

            return CompanyProblemDetail(
                id=problem_id,
                title=p["title"],
                slug=p["slug"],
                leetcode_url=p["leetcode_url"],
                difficulty=p["difficulty"],
                frequency_score=p["frequency_score"],
                acceptance_rate=p["acceptance_rate"],
                topics=p["topics"],
                order_index=order_index,
                is_unlocked=True,
                is_solved=is_solved,
                description=f"Solve on LeetCode: {p['leetcode_url']}",
                starter_code={"python": f"# LeetCode: {p['leetcode_url']}\n"},
                test_cases=[]
            )

        # 2. Database problem ID
        result = await db.execute(
            select(CompanyProblem)
            .options(selectinload(CompanyProblem.track))
            .where(CompanyProblem.id == problem_id)
        )
        problem = result.scalar_one_or_none()
        if not problem:
            raise EntityNotFoundError("CompanyProblem", problem_id)

        progress = await cls.get_or_create_user_progress(db, user_id, problem.company_track_id)
        effective_unlocked = max(problem.track.initial_unlocked_count, progress.unlocked_count)
        is_unlocked = problem.order_index <= effective_unlocked
        is_solved = problem.id in (progress.solved_problem_ids or [])

        if not is_unlocked:
            raise AppException(
                f"This question is locked in the {problem.track.name} Track. Solve earlier questions to unlock.",
                code="PROBLEM_LOCKED",
                status_code=403
            )

        return CompanyProblemDetail(
            id=problem.id,
            title=problem.title,
            slug=problem.slug,
            leetcode_url=f"https://leetcode.com/problems/{problem.slug}/",
            difficulty=problem.difficulty,
            frequency_score=problem.frequency_score,
            acceptance_rate=problem.acceptance_rate,
            topics=problem.topics or [],
            order_index=problem.order_index,
            is_unlocked=True,
            is_solved=is_solved,
            description=problem.description,
            starter_code=problem.starter_code or {},
            test_cases=problem.test_cases or []
        )

    @classmethod
    async def solve_and_unlock(
        cls, db: AsyncSession, user_id: str, problem_id: str, code: str, language: str
    ) -> SolveCompanyProblemResponse:
        # Check if dynamic CSV problem ID
        if problem_id.startswith("p-") or problem_id.startswith("prob-"):
            parts = problem_id.split("-")
            slug = "-".join(parts[1:-1]) if len(parts) >= 3 and parts[-1].isdigit() else parts[1]
            order_index = int(parts[-1]) if len(parts) >= 3 and parts[-1].isdigit() else 1

            track_res = await db.execute(select(CompanyTrack).where(CompanyTrack.slug == slug))
            track = track_res.scalar_one_or_none()
            if not track:
                raise EntityNotFoundError("CompanyProblem", problem_id)

            progress = await cls.get_or_create_user_progress(db, user_id, track.id)
            effective_unlocked = max(track.initial_unlocked_count, progress.unlocked_count)
            if order_index > effective_unlocked:
                raise AppException(
                    "Cannot solve a locked problem.",
                    code="PROBLEM_LOCKED",
                    status_code=403
                )

            solved_list = list(progress.solved_problem_ids or [])
            if problem_id not in solved_list:
                solved_list.append(problem_id)
                progress.solved_problem_ids = solved_list
                progress.solved_count = len(solved_list)

            csv_probs = load_company_problems_from_csv(slug)
            track_total = len(csv_probs) if csv_probs else track.total_problems
            unlocked_new = False
            new_unlocked_title = None
            if progress.unlocked_count < track_total:
                progress.unlocked_count += 1
                unlocked_new = True
                next_prob = next((p for p in csv_probs if p["order_index"] == progress.unlocked_count), None)
                if next_prob:
                    new_unlocked_title = next_prob["title"]

            progress.last_practiced_at = datetime.now(timezone.utc)
            await db.commit()

            return SolveCompanyProblemResponse(
                status="passed",
                tests_passed=1,
                tests_total=1,
                stdout="Submitted on LeetCode",
                stderr="",
                unlocked_new_problem=unlocked_new,
                new_unlocked_problem_title=new_unlocked_title,
                total_unlocked=progress.unlocked_count,
                total_solved=progress.solved_count
            )

        problem_res = await db.execute(
            select(CompanyProblem)
            .options(selectinload(CompanyProblem.track))
            .where(CompanyProblem.id == problem_id)
        )
        problem = problem_res.scalar_one_or_none()
        if not problem:
            raise EntityNotFoundError("CompanyProblem", problem_id)

        # Execute in sandbox or simulate pass
        from backend.app.coding.runner import ExecutionRunner
        test_cases = problem.test_cases or []
        execution_res = await ExecutionRunner.execute_code(language, code, test_cases)

        status_str = execution_res.get("status", "passed")
        tests_passed = execution_res.get("tests_passed", len(test_cases))
        tests_total = execution_res.get("tests_total", len(test_cases) or 1)

        progress = await cls.get_or_create_user_progress(db, user_id, problem.company_track_id)
        unlocked_new = False
        new_unlocked_title = None

        if status_str == "passed":
            solved_list = list(progress.solved_problem_ids or [])
            if problem.id not in solved_list:
                solved_list.append(problem.id)
                progress.solved_problem_ids = solved_list
                progress.solved_count = len(solved_list)

            # Unlock next question if available
            csv_probs = load_company_problems_from_csv(problem.track.slug)
            track_total = len(csv_probs) if csv_probs else problem.track.total_problems
            if progress.unlocked_count < track_total:
                progress.unlocked_count += 1
                unlocked_new = True
                # Find the newly unlocked problem title
                next_p_res = await db.execute(
                    select(CompanyProblem).where(
                        CompanyProblem.company_track_id == problem.company_track_id,
                        CompanyProblem.order_index == progress.unlocked_count
                    )
                )
                next_p = next_p_res.scalar_one_or_none()
                if next_p:
                    new_unlocked_title = next_p.title
                elif csv_probs:
                    next_csv_p = next((p for p in csv_probs if p["order_index"] == progress.unlocked_count), None)
                    if next_csv_p:
                        new_unlocked_title = next_csv_p["title"]

            progress.last_practiced_at = datetime.now(timezone.utc)
            await db.commit()


        return SolveCompanyProblemResponse(
            status=status_str,
            tests_passed=tests_passed,
            tests_total=tests_total,
            stdout=execution_res.get("stdout", ""),
            stderr=execution_res.get("stderr", ""),
            unlocked_new_problem=unlocked_new,
            new_unlocked_problem_title=new_unlocked_title,
            total_unlocked=progress.unlocked_count,
            total_solved=progress.solved_count
        )

    @classmethod
    async def toggle_problem_solved(
        cls, db: AsyncSession, user_id: str, problem_id: str
    ) -> ToggleProblemSolvedResponse:
        await cls.seed_tracks_if_empty(db)

        # 1. Handle dynamic CSV problem IDs: p-{slug}-{order_index}
        if problem_id.startswith("p-") or problem_id.startswith("prob-"):
            parts = problem_id.split("-")
            if len(parts) >= 3 and parts[-1].isdigit():
                slug = "-".join(parts[1:-1])
                order_index = int(parts[-1])
            else:
                slug = parts[1]
                order_index = 1

            track_res = await db.execute(select(CompanyTrack).where(CompanyTrack.slug == slug))
            track = track_res.scalar_one_or_none()
            if not track:
                comp_reg = CompanyRegistry.get_company_by_slug(slug)
                name = comp_reg["name"] if comp_reg else slug.replace("-", " ").title()
                track = CompanyTrack(
                    name=name,
                    slug=slug,
                    tier="silver",
                    role_title="Software Development Engineer",
                    description="",
                    community_tips=[],
                    total_problems=100,
                    initial_unlocked_count=3,
                    logo_icon="Building2",
                )
                db.add(track)
                await db.flush()

            progress = await cls.get_or_create_user_progress(db, user_id, track.id)
            effective_unlocked = max(track.initial_unlocked_count, progress.unlocked_count)
            if order_index > effective_unlocked:
                raise AppException(
                    "Cannot solve a locked problem. Complete earlier problems to unlock.",
                    code="PROBLEM_LOCKED",
                    status_code=403
                )

            csv_probs = load_company_problems_from_csv(slug)
            track_total = len(csv_probs) if csv_probs else track.total_problems

            solved_list = list(progress.solved_problem_ids or [])
            unlocked_new = False
            new_unlocked_title = None

            if problem_id in solved_list:
                solved_list.remove(problem_id)
                progress.solved_problem_ids = solved_list
                progress.solved_count = len(solved_list)
                is_now_solved = False
            else:
                solved_list.append(problem_id)
                progress.solved_problem_ids = solved_list
                progress.solved_count = len(solved_list)
                is_now_solved = True

                if progress.unlocked_count < track_total:
                    progress.unlocked_count += 1
                    unlocked_new = True
                    next_prob = next((p for p in csv_probs if p["order_index"] == progress.unlocked_count), None)
                    if next_prob:
                        new_unlocked_title = next_prob["title"]

            progress.last_practiced_at = datetime.now(timezone.utc)
            await db.commit()

            return ToggleProblemSolvedResponse(
                problem_id=problem_id,
                is_solved=is_now_solved,
                unlocked_new_problem=unlocked_new,
                new_unlocked_problem_title=new_unlocked_title,
                unlocked_count=progress.unlocked_count,
                solved_count=progress.solved_count
            )

        # 2. Database problem ID
        problem_res = await db.execute(
            select(CompanyProblem)
            .options(selectinload(CompanyProblem.track))
            .where(CompanyProblem.id == problem_id)
        )
        problem = problem_res.scalar_one_or_none()
        if not problem:
            raise EntityNotFoundError("CompanyProblem", problem_id)

        progress = await cls.get_or_create_user_progress(db, user_id, problem.company_track_id)
        effective_unlocked = max(problem.track.initial_unlocked_count, progress.unlocked_count)
        if problem.order_index > effective_unlocked:
            raise AppException(
                "Cannot solve a locked problem. Complete earlier problems to unlock.",
                code="PROBLEM_LOCKED",
                status_code=403
            )

        solved_list = list(progress.solved_problem_ids or [])
        unlocked_new = False
        new_unlocked_title = None

        if problem.id in solved_list:
            solved_list.remove(problem.id)
            progress.solved_problem_ids = solved_list
            progress.solved_count = len(solved_list)
            is_now_solved = False
        else:
            solved_list.append(problem.id)
            progress.solved_problem_ids = solved_list
            progress.solved_count = len(solved_list)
            is_now_solved = True

            # If this problem order reached current unlocked, unlock next problem
            csv_probs = load_company_problems_from_csv(problem.track.slug)
            track_total = len(csv_probs) if csv_probs else problem.track.total_problems
            if progress.unlocked_count < track_total:
                progress.unlocked_count += 1
                unlocked_new = True
                next_p_res = await db.execute(
                    select(CompanyProblem).where(
                        CompanyProblem.company_track_id == problem.company_track_id,
                        CompanyProblem.order_index == progress.unlocked_count
                    )
                )
                next_p = next_p_res.scalar_one_or_none()
                if next_p:
                    new_unlocked_title = next_p.title
                elif csv_probs:
                    next_csv_p = next((p for p in csv_probs if p["order_index"] == progress.unlocked_count), None)
                    if next_csv_p:
                        new_unlocked_title = next_csv_p["title"]

        progress.last_practiced_at = datetime.now(timezone.utc)
        await db.commit()

        return ToggleProblemSolvedResponse(
            problem_id=problem.id,
            is_solved=is_now_solved,
            unlocked_new_problem=unlocked_new,
            new_unlocked_problem_title=new_unlocked_title,
            unlocked_count=progress.unlocked_count,
            solved_count=progress.solved_count
        )

    @classmethod
    def get_all_simulations(cls) -> List[PresetSimulationResponse]:
        sims = CompanyRegistry.get_all_simulations()
        return [PresetSimulationResponse(**s) for s in sims]

    @classmethod
    def get_simulation_by_id(cls, sim_id: str) -> Optional[PresetSimulationResponse]:
        sim = CompanyRegistry.get_simulation_by_id(sim_id)
        if not sim:
            raise EntityNotFoundError("PlacementSimulation", sim_id)
        return PresetSimulationResponse(**sim)
