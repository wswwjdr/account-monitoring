"""分组的创建、重命名、删除与校验。"""

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.config import UNGROUPED_LABEL
from app.models import Account, Group, utc_now


def _normalize_name(name: str) -> str:
    """去掉首尾空白；空名称或与「未分组」冲突则立即失败。"""
    if name is None:
        raise ValueError("分组名不能为空")
    value = name.strip()
    if not value:
        raise ValueError("分组名不能为空")
    if value == UNGROUPED_LABEL:
        raise ValueError(f"「{UNGROUPED_LABEL}」是系统展示名，不能用作分组名")
    return value


def require_group(db: Session, group_id: int) -> Group:
    """按 id 取分组，不存在则失败。"""
    group = db.get(Group, group_id)
    if group is None:
        raise ValueError("分组不存在")
    return group


def resolve_group_id(db: Session, group_id: int | None) -> int | None:
    """导入用的分组：空表示未分组，有值则必须存在。"""
    if group_id is None:
        return None
    require_group(db, group_id)
    return group_id


def find_group_by_name(db: Session, name: str, exclude_id: int | None = None) -> Group | None:
    """按名称精确查找分组，可选排除自身（用于重命名查重）。"""
    stmt = select(Group).where(Group.name == name)
    if exclude_id is not None:
        stmt = stmt.where(Group.id != exclude_id)
    return db.scalars(stmt).first()


def list_groups_with_counts(db: Session) -> list[tuple[Group, int]]:
    """列出全部分组及各自账号数量。"""
    count_stmt = (
        select(Account.group_id, func.count(Account.id))
        .where(Account.group_id.is_not(None))
        .group_by(Account.group_id)
    )
    counts = {row[0]: int(row[1]) for row in db.execute(count_stmt).all()}
    groups = list(db.scalars(select(Group).order_by(Group.id.asc())).all())
    return [(group, counts.get(group.id, 0)) for group in groups]


def create_group(db: Session, name: str) -> Group:
    """新建分组；名称冲突立即失败。"""
    normalized = _normalize_name(name)
    if find_group_by_name(db, normalized) is not None:
        raise ValueError("分组名已存在")
    now = utc_now()
    group = Group(
        name=normalized,
        created_at=now,
        updated_at=now,
    )
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


def rename_group(db: Session, group_id: int, name: str) -> Group:
    """重命名分组；与其它分组重名则失败。"""
    group = require_group(db, group_id)
    normalized = _normalize_name(name)
    conflict = find_group_by_name(db, normalized, exclude_id=group.id)
    if conflict is not None:
        raise ValueError("分组名已存在")
    group.name = normalized
    group.updated_at = utc_now()
    db.commit()
    db.refresh(group)
    return group


def delete_group(db: Session, group_id: int) -> None:
    """删除分组，组内账号变为未分组。"""
    group = require_group(db, group_id)
    db.execute(update(Account).where(Account.group_id == group.id).values(group_id=None))
    db.delete(group)
    db.commit()
