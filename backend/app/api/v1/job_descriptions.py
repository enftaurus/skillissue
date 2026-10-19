from typing import List
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.database.session import get_db
from backend.app.database.models import User
from backend.app.auth.dependencies import get_current_active_user
from backend.app.job_descriptions.schemas import (
    JobDescriptionCreate, JobDescriptionUpdate, JobDescriptionResponse
)
from backend.app.job_descriptions.service import JobDescriptionService

router = APIRouter(prefix="/job-descriptions", tags=["Job Descriptions"])

@router.post("", response_model=JobDescriptionResponse, status_code=status.HTTP_201_CREATED)
async def create_job_description(
    data: JobDescriptionCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await JobDescriptionService.create_and_extract(db, current_user.id, data)

@router.get("", response_model=List[JobDescriptionResponse])
async def list_job_descriptions(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await JobDescriptionService.list_jds(db, current_user.id)

@router.get("/{jd_id}", response_model=JobDescriptionResponse)
async def get_job_description(
    jd_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await JobDescriptionService.get_jd(db, current_user.id, jd_id)

@router.put("/{jd_id}", response_model=JobDescriptionResponse)
async def update_job_description(
    jd_id: str,
    data: JobDescriptionUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    return await JobDescriptionService.update_jd(db, current_user.id, jd_id, data)

@router.delete("/{jd_id}", status_code=status.HTTP_200_OK)
async def delete_job_description(
    jd_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    await JobDescriptionService.delete_jd(db, current_user.id, jd_id)
    return {"status": "deleted", "id": jd_id}
