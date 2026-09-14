"""账号批量删除与批量改分组。"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Account, utc_now
from app.services.group_service import resolve_group_id


def _load_selected_accounts(db: Session, ids: list[int]) -> list[Account]:
    """按 id 取出账号；空列表或有缺失立即失败。"""
    if not ids:
        raise ValueError("未选择账号")
    unique_ids = list(dict.fromkeys(ids))
    if any(item < 1 for item in unique_ids):
        raise ValueError("账号 id 无效")
    accounts = list(db.scalars(select(Account).where(Account.id.in_(unique_ids))).all())
    if len(accounts) != len(unique_ids):
        raise ValueError("部分账号不存在")
    return accounts


def batch_delete_accounts(db: Session, ids: list[int]) -> int:
    """删除选中的账号版本，返回删除条数。"""
    accounts = _load_selected_accounts(db, ids)
    for account in accounts:
        db.delete(account)
    db.commit()
    return len(accounts)


def batch_move_accounts(db: Session, ids: list[int], group_id: int | None) -> int:
    """把选中账号改到指定分组；group_id 为空表示未分组。"""
    resolved_group_id = resolve_group_id(db, group_id)
    accounts = _load_selected_accounts(db, ids)
    now = utc_now()
    for account in accounts:
        account.group_id = resolved_group_id
        account.updated_at = now
    db.commit()
    return len(accounts)
