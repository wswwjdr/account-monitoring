"""分组列表、新建、重命名、删除。"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Account, Group
from app.schemas import GroupOut, GroupWriteBody
from app.services.group_service import (
    create_group,
    delete_group,
    list_groups_with_counts,
    rename_group,
)

router = APIRouter(prefix="/api/groups", tags=["groups"])


def _to_out(group: Group, account_count: int) -> GroupOut:
    """把分组实体转成响应模型。"""
    return GroupOut(
        id=group.id,
        name=group.name,
        account_count=account_count,
        created_at=group.created_at,
        updated_at=group.updated_at,
    )


@router.get("", response_model=list[GroupOut])
def list_groups(db: Session = Depends(get_db)) -> list[GroupOut]:
    return [_to_out(group, count) for group, count in list_groups_with_counts(db)]


@router.post("", response_model=GroupOut, status_code=201)
def add_group(body: GroupWriteBody, db: Session = Depends(get_db)) -> GroupOut:
    try:
        group = create_group(db, body.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _to_out(group, 0)


@router.patch("/{group_id}", response_model=GroupOut)
def update_group(group_id: int, body: GroupWriteBody, db: Session = Depends(get_db)) -> GroupOut:
    try:
        group = rename_group(db, group_id, body.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    count = db.scalar(select(func.count(Account.id)).where(Account.group_id == group.id)) or 0
    return _to_out(group, count)


@router.delete("/{group_id}", status_code=204)
def remove_group(group_id: int, db: Session = Depends(get_db)) -> None:
    try:
        delete_group(db, group_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
