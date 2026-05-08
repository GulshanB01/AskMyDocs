from typing import List

from fastapi import APIRouter, Depends, HTTPException, status

from backend.schemas import TagRequest, TagResponse
from backend.security import get_current_api_user
from db import Tags, Users


router = APIRouter(prefix="/tags", tags=["Tags"])


def serialize_tag(tag: Tags) -> TagResponse:
    return TagResponse(id=tag.id, name=tag.name)


@router.get("", response_model=List[TagResponse])
def list_tags(current_user: Users = Depends(get_current_api_user)):
    tags = Tags.select().where(Tags.user_id == current_user.id).order_by(Tags.name.asc())
    return [serialize_tag(tag) for tag in tags]


@router.post("", response_model=TagResponse, status_code=status.HTTP_201_CREATED)
def create_tag(payload: TagRequest, current_user: Users = Depends(get_current_api_user)):
    tag_name = payload.name.strip()
    if not tag_name:
        raise HTTPException(status_code=400, detail="Tag name is required.")
    tag = Tags.create(name=tag_name, user_id=current_user.id)
    return serialize_tag(tag)


@router.delete("/{tag_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tag(tag_id: int, current_user: Users = Depends(get_current_api_user)):
    deleted_count = (
        Tags.delete()
        .where(
            (Tags.id == tag_id)
            & (Tags.user_id == current_user.id)
        )
        .execute()
    )
    if not deleted_count:
        raise HTTPException(status_code=404, detail="Tag not found.")
    return None
