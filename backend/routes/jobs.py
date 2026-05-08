from typing import List

from fastapi import APIRouter, Depends, HTTPException

from backend.schemas import JobResponse
from backend.security import get_current_api_user
from db import DocumentProcessingJobs, Users


router = APIRouter(prefix="/jobs", tags=["Jobs"])


def serialize_job(job: DocumentProcessingJobs) -> JobResponse:
    return JobResponse(
        id=job.id,
        document_name=job.document_name,
        status=job.status,
        progress=job.progress,
        message=job.message,
        error=job.error,
        created_at=job.created_at.isoformat(),
        updated_at=job.updated_at.isoformat(),
    )


@router.get("", response_model=List[JobResponse])
def list_jobs(current_user: Users = Depends(get_current_api_user)):
    jobs = (
        DocumentProcessingJobs.select()
        .where(DocumentProcessingJobs.user_id == current_user.id)
        .order_by(DocumentProcessingJobs.created_at.desc())
        .limit(10)
    )
    return [serialize_job(job) for job in jobs]


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: int, current_user: Users = Depends(get_current_api_user)):
    job = DocumentProcessingJobs.get_or_none(
        (DocumentProcessingJobs.id == job_id)
        & (DocumentProcessingJobs.user_id == current_user.id)
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")
    return serialize_job(job)
