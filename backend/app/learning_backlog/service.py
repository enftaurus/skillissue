from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from backend.app.database.models import LearningBacklogItem, Evaluation
from backend.app.learning_backlog.schemas import (
    BacklogItemCreate,
    BacklogItemUpdate,
    QueueWeaknessRequest,
    BacklogItemResponse,
)
from backend.app.core.errors import EntityNotFoundError, AppException
from backend.app.core.logging import logger

class LearningBacklogService:
    @staticmethod
    async def list_items(
        db: AsyncSession,
        user_id: str,
        status: Optional[str] = None,
        topic: Optional[str] = None,
    ) -> List[LearningBacklogItem]:
        query = select(LearningBacklogItem).where(LearningBacklogItem.user_id == user_id)
        if status:
            query = query.where(LearningBacklogItem.status == status)
        if topic:
            query = query.where(func.lower(LearningBacklogItem.topic).contains(topic.lower()))

        query = query.order_by(LearningBacklogItem.created_at.desc())
        result = await db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    async def get_item(
        db: AsyncSession,
        user_id: str,
        item_id: str,
    ) -> LearningBacklogItem:
        result = await db.execute(
            select(LearningBacklogItem).where(
                LearningBacklogItem.id == item_id,
                LearningBacklogItem.user_id == user_id,
            )
        )
        item = result.scalar_one_or_none()
        if not item:
            raise EntityNotFoundError("LearningBacklogItem", item_id)
        return item

    @staticmethod
    async def queue_weakness(
        db: AsyncSession,
        user_id: str,
        data: QueueWeaknessRequest,
    ) -> BacklogItemResponse:
        """
        Action B: Queue weakness for later without allocating dates or altering existing sprints.
        Enforces sensible deduplication: if the topic is already queued or planned, update rather than duplicate.
        """
        normalized_topic = data.topic.strip()

        # Check for existing active item with same topic for this user
        existing_res = await db.execute(
            select(LearningBacklogItem).where(
                LearningBacklogItem.user_id == user_id,
                func.lower(LearningBacklogItem.topic) == normalized_topic.lower(),
                LearningBacklogItem.status.in_(["queued", "planned", "in_progress"]),
            )
        )
        existing = existing_res.scalar_one_or_none()

        if existing:
            # Topic already queued: preserve existing entry, append context if new notes provided
            if data.notes and data.notes not in (existing.notes or ""):
                existing.notes = f"{existing.notes}\n{data.notes}".strip() if existing.notes else data.notes
            if data.learning_objective and not existing.learning_objective:
                existing.learning_objective = data.learning_objective
            if data.suggested_exercise and not existing.suggested_exercise:
                existing.suggested_exercise = data.suggested_exercise

            existing.updated_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(existing)

            resp = BacklogItemResponse.model_validate(existing)
            resp.is_existing = True
            logger.info(f"Deduplicated queue request: Topic '{normalized_topic}' already exists in backlog for user {user_id}")
            return resp

        # Create fresh queued backlog item
        reason_text = data.gap_explanation or data.evidence or "Identified as growth opportunity in interview."
        item = LearningBacklogItem(
            user_id=user_id,
            topic=normalized_topic,
            subtopic=data.subtopic.strip() if data.subtopic else None,
            source="interview_evaluation" if data.interview_id else "manual",
            source_id=data.interview_id,
            reason=reason_text,
            learning_objective=data.learning_objective,
            suggested_exercise=data.suggested_exercise,
            priority=data.priority,
            status="queued",
            notes=data.notes,
        )
        db.add(item)

        # If linked to interview evaluation, update weakness item status
        if data.interview_id:
            eval_res = await db.execute(
                select(Evaluation).where(
                    Evaluation.interview_id == data.interview_id,
                    Evaluation.user_id == user_id,
                )
            )
            evaluation = eval_res.scalar_one_or_none()
            if evaluation and evaluation.weakness_analysis:
                updated_analysis = []
                for w in evaluation.weakness_analysis:
                    if (
                        (data.weakness_id and w.get("id") == data.weakness_id)
                        or w.get("topic", "").lower() == normalized_topic.lower()
                    ):
                        w_copy = dict(w)
                        w_copy["status"] = "queued"
                        updated_analysis.append(w_copy)
                    else:
                        updated_analysis.append(w)
                evaluation.weakness_analysis = updated_analysis

        await db.commit()
        await db.refresh(item)

        resp = BacklogItemResponse.model_validate(item)
        resp.is_existing = False
        return resp

    @staticmethod
    async def create_item(
        db: AsyncSession,
        user_id: str,
        data: BacklogItemCreate,
    ) -> BacklogItemResponse:
        normalized_topic = data.topic.strip()
        item = LearningBacklogItem(
            user_id=user_id,
            topic=normalized_topic,
            subtopic=data.subtopic.strip() if data.subtopic else None,
            source=data.source,
            source_id=data.source_id,
            reason=data.reason or "",
            learning_objective=data.learning_objective,
            suggested_exercise=data.suggested_exercise,
            priority=data.priority,
            status="queued",
            notes=data.notes,
        )
        db.add(item)
        await db.commit()
        await db.refresh(item)
        resp = BacklogItemResponse.model_validate(item)
        resp.is_existing = False
        return resp

    @staticmethod
    async def update_item(
        db: AsyncSession,
        user_id: str,
        item_id: str,
        data: BacklogItemUpdate,
    ) -> LearningBacklogItem:
        item = await LearningBacklogService.get_item(db, user_id, item_id)
        if data.topic is not None:
            item.topic = data.topic.strip()
        if data.subtopic is not None:
            item.subtopic = data.subtopic.strip() if data.subtopic else None
        if data.status is not None:
            item.status = data.status
        if data.priority is not None:
            item.priority = data.priority
        if data.notes is not None:
            item.notes = data.notes
        if data.learning_objective is not None:
            item.learning_objective = data.learning_objective
        if data.suggested_exercise is not None:
            item.suggested_exercise = data.suggested_exercise

        item.updated_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(item)
        return item

    @staticmethod
    async def delete_item(
        db: AsyncSession,
        user_id: str,
        item_id: str,
    ) -> bool:
        item = await LearningBacklogService.get_item(db, user_id, item_id)
        await db.delete(item)
        await db.commit()
        return True
