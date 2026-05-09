from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional

from backend.db import DocumentProcessingJobs, db
from backend.services.document_processing import upload_document_sync


_executor = ThreadPoolExecutor(max_workers=2)


def _mark_job(
    job_id: int,
    *,
    status: Optional[str] = None,
    progress: Optional[int] = None,
    message: Optional[str] = None,
    error: Optional[str] = None,
):
    updates = {DocumentProcessingJobs.updated_at: datetime.utcnow()}
    if status is not None:
        updates[DocumentProcessingJobs.status] = status
    if progress is not None:
        updates[DocumentProcessingJobs.progress] = progress
    if message is not None:
        updates[DocumentProcessingJobs.message] = message
    if error is not None:
        updates[DocumentProcessingJobs.error] = error
    DocumentProcessingJobs.update(updates).where(DocumentProcessingJobs.id == job_id).execute()


def _run_job(job_id: int, user_id: int, document_name: str, pdf_bytes: bytes):
    if db.is_closed():
        db.connect(reuse_if_open=True)

    try:
        _mark_job(job_id, status="processing", progress=1, message="Starting")

        def progress_callback(progress: int, message: str):
            _mark_job(job_id, status="processing", progress=progress, message=message)

        upload_document_sync(
            user_id,
            document_name,
            pdf_bytes,
            progress_callback,
            document_processing_job_id=job_id,
        )
        _mark_job(job_id, status="completed", progress=100, message="Completed")
    except Exception as exc:
        _mark_job(job_id, status="failed", message="Failed", error=str(exc))
        raise


def enqueue_document_processing(user_id: int, document_name: str, pdf_bytes: bytes) -> DocumentProcessingJobs:
    job = DocumentProcessingJobs.create(
        user_id=user_id,
        document_name=document_name,
        status="queued",
        progress=0,
        message="Queued",
    )
    _executor.submit(_run_job, job.id, user_id, document_name, pdf_bytes)
    return job
