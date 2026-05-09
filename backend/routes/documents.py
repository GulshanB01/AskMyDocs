from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from backend.services.background_queue import enqueue_document_processing
from backend.schemas import DocumentResponse, DocumentUploadResponse
from backend.security import get_current_api_user
from backend.db import DocumentTags, Documents, Tags, Users


router = APIRouter(prefix="/documents", tags=["Documents"])


def serialize_document(document: Documents) -> DocumentResponse:
    tag_rows = (
        Tags.select(Tags.name)
        .join(DocumentTags)
        .where(DocumentTags.document_id == document.id)
    )
    return DocumentResponse(
        id=document.id,
        name=document.name,
        tags=[tag.name for tag in tag_rows],
    )


@router.post("/upload", response_model=DocumentUploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: Users = Depends(get_current_api_user),
):
    if file.content_type and file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    job = enqueue_document_processing(current_user.id, file.filename or "document.pdf", pdf_bytes)
    return DocumentUploadResponse(
        job_id=job.id,
        status=job.status,
        document_name=job.document_name,
    )


@router.get("", response_model=List[DocumentResponse])
def list_documents(current_user: Users = Depends(get_current_api_user)):
    documents = Documents.select().where(Documents.user_id == current_user.id).order_by(Documents.id.desc())
    return [serialize_document(document) for document in documents]


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: int, current_user: Users = Depends(get_current_api_user)):
    document = Documents.get_or_none(
        (Documents.id == document_id)
        & (Documents.user_id == current_user.id)
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found.")
    return serialize_document(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: int, current_user: Users = Depends(get_current_api_user)):
    deleted_count = (
        Documents.delete()
        .where(
            (Documents.id == document_id)
            & (Documents.user_id == current_user.id)
        )
        .execute()
    )
    if not deleted_count:
        raise HTTPException(status_code=404, detail="Document not found.")
    return None
