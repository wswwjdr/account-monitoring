"""账号导入：预览冲突、追加新版本、覆盖最新、清空后导入。冲突与清空均限定在所选分类内。"""

from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.account_types import require_account_type
from app.models import Account, utc_now
from app.services.group_service import resolve_group_id
from app.services.import_parser import ParsedAccount, normalize_email, parse_import_text


@dataclass(frozen=True)
class ImportPreview:
    """导入预览：将写入行数、该分类下不存在的邮箱、已存在的冲突邮箱。"""

    line_count: int
    new_emails: list[str]
    conflict_emails: list[str]


@dataclass(frozen=True)
class ImportResult:
    """导入落库结果。"""

    inserted: int
    updated: int
    wiped: bool


def _existing_email_keys(db: Session, account_type: str) -> set[str]:
    """读取指定分类下已有邮箱的小写集合。"""
    emails = db.scalars(select(Account.email).where(Account.account_type == account_type)).all()
    return {normalize_email(item) for item in emails}


def _find_latest_by_email(db: Session, email: str, account_type: str) -> Account | None:
    """取某分类下某邮箱 imported_at 最大的一条；并列时取 id 更大者。"""
    key = normalize_email(email)
    stmt = (
        select(Account)
        .where(Account.account_type == account_type)
        .where(func.lower(Account.email) == key)
        .order_by(Account.imported_at.desc(), Account.id.desc())
        .limit(1)
    )
    return db.scalars(stmt).first()


def _new_account(parsed: ParsedAccount, group_id: int | None, account_type: str) -> Account:
    """由解析行构造一条待插入账号；group_id 为空即未分组。"""
    now = utc_now()
    return Account(
        group_id=group_id,
        account_type=account_type,
        email=parsed.email,
        password=parsed.password,
        client_id=parsed.client_id,
        refresh_token=parsed.refresh_token,
        imported_at=now,
        access_token=None,
        token_expires_at=None,
        token_status="unknown",
        token_error=None,
        token_endpoint=None,
        created_at=now,
        updated_at=now,
    )


def _overwrite_latest(target: Account, parsed: ParsedAccount, group_id: int | None) -> None:
    """用新凭证覆盖最新版本，并改到本次选择的分组（可为空表示未分组）。分类保持不变。"""
    now = utc_now()
    target.group_id = group_id
    target.email = parsed.email
    target.password = parsed.password
    target.client_id = parsed.client_id
    target.refresh_token = parsed.refresh_token
    target.imported_at = now
    target.access_token = None
    target.token_expires_at = None
    target.token_status = "unknown"
    target.token_error = None
    target.token_endpoint = None
    target.updated_at = now


def preview_import(db: Session, text: str, account_type: str) -> ImportPreview:
    """解析文本并对照该分类现有库，不写库。"""
    code = require_account_type(account_type)
    rows = parse_import_text(text, code)
    existing = _existing_email_keys(db, code)
    seen_new: list[str] = []
    seen_conflict: list[str] = []
    seen_keys: set[str] = set()
    for row in rows:
        key = normalize_email(row.email)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        if key in existing:
            seen_conflict.append(row.email)
        else:
            seen_new.append(row.email)
    return ImportPreview(
        line_count=len(rows),
        new_emails=seen_new,
        conflict_emails=seen_conflict,
    )


def apply_import(
    db: Session,
    text: str,
    group_id: int | None,
    conflict_mode: str | None,
    wipe_all: bool,
    account_type: str,
) -> ImportResult:
    """按模式写入账号。group_id 为空表示未分组。清空与冲突均只作用于所选分类。"""
    code = require_account_type(account_type)
    resolved_group_id = resolve_group_id(db, group_id)
    rows = parse_import_text(text, code)
    if wipe_all:
        db.execute(delete(Account).where(Account.account_type == code))
        db.flush()
        for row in rows:
            db.add(_new_account(row, resolved_group_id, code))
        db.commit()
        return ImportResult(inserted=len(rows), updated=0, wiped=True)

    existing = _existing_email_keys(db, code)
    conflict_keys = {normalize_email(row.email) for row in rows if normalize_email(row.email) in existing}
    if conflict_keys and conflict_mode not in {"append", "replace_latest"}:
        raise ValueError("存在重复邮箱，必须指定 conflict_mode 为 append 或 replace_latest")

    inserted = 0
    updated = 0
    for row in rows:
        latest = _find_latest_by_email(db, row.email, code)
        if latest is None:
            db.add(_new_account(row, resolved_group_id, code))
            db.flush()
            inserted += 1
            continue
        if conflict_mode == "replace_latest":
            _overwrite_latest(latest, row, resolved_group_id)
            updated += 1
            continue
        db.add(_new_account(row, resolved_group_id, code))
        db.flush()
        inserted += 1

    db.commit()
    return ImportResult(inserted=inserted, updated=updated, wiped=False)
