"""账号列表、导入预览/落库、单条删除。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.account_types import get_account_type
from app.config import UNGROUPED_LABEL
from app.db import get_db
from app.models import Account
from app.schemas import (
    AccountBatchMoveBody,
    AccountIdsBody,
    AccountImportInfoOut,
    AccountOut,
    BatchChangeOut,
    ImportApplyBody,
    ImportPreviewOut,
    ImportResultOut,
    ImportTextBody,
)
from app.services.account_batch import batch_delete_accounts, batch_move_accounts
from app.services.account_import import apply_import, preview_import

router = APIRouter(prefix="/api/accounts", tags=["accounts"])

IMPORT_LINE_SEPARATOR = "----"


def _to_out(account: Account) -> AccountOut:
    """序列化账号摘要；不含密码、Client ID、刷新令牌。无分组时名称为未分组。"""
    spec = get_account_type(account.account_type)
    return AccountOut(
        id=account.id,
        group_id=account.group_id,
        group_name=account.group.name if account.group is not None else UNGROUPED_LABEL,
        account_type=spec.code,
        account_type_label=spec.label,
        supports_mail=spec.supports_mail,
        email=account.email,
        imported_at=account.imported_at,
        token_status=account.token_status,
        token_error=account.token_error,
        created_at=account.created_at,
        updated_at=account.updated_at,
    )


def _to_import_info(account: Account) -> AccountImportInfoOut:
    """序列化导入凭证；用 ---- 拼回一行便于复制。"""
    import_line = IMPORT_LINE_SEPARATOR.join(
        [account.email, account.password, account.client_id, account.refresh_token]
    )
    return AccountImportInfoOut(
        email=account.email,
        password=account.password,
        client_id=account.client_id,
        refresh_token=account.refresh_token,
        import_line=import_line,
    )


@router.get("", response_model=list[AccountOut])
def list_accounts(
    q: str | None = Query(default=None),
    group_id: int | None = Query(default=None),
    ungrouped: bool = Query(default=False),
    account_type: str | None = Query(default=None),
    db: Session = Depends(get_db),
) -> list[AccountOut]:
    if ungrouped and group_id is not None:
        raise HTTPException(status_code=400, detail="不能同时指定分组与未分组")
    stmt = (
        select(Account)
        .options(joinedload(Account.group))
        .order_by(Account.email.asc(), Account.imported_at.desc(), Account.id.desc())
    )
    if q:
        keyword = q.strip()
        if keyword:
            stmt = stmt.where(func.lower(Account.email).contains(keyword.lower()))
    if ungrouped:
        stmt = stmt.where(Account.group_id.is_(None))
    elif group_id is not None:
        stmt = stmt.where(Account.group_id == group_id)
    if account_type:
        try:
            spec = get_account_type(account_type)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        stmt = stmt.where(Account.account_type == spec.code)
    return [_to_out(account) for account in db.scalars(stmt).unique().all()]


@router.get("/{account_id}", response_model=AccountOut)
def get_account(account_id: int, db: Session = Depends(get_db)) -> AccountOut:
    account = db.scalars(
        select(Account).options(joinedload(Account.group)).where(Account.id == account_id)
    ).first()
    if account is None:
        raise HTTPException(status_code=404, detail="账号不存在")
    return _to_out(account)


@router.get("/{account_id}/import-info", response_model=AccountImportInfoOut)
def get_account_import_info(account_id: int, db: Session = Depends(get_db)) -> AccountImportInfoOut:
    """查看导入该账号时的四段凭证；不进入列表摘要。"""
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="账号不存在")
    return _to_import_info(account)


@router.post("/import/preview", response_model=ImportPreviewOut)
def preview_accounts(body: ImportTextBody, db: Session = Depends(get_db)) -> ImportPreviewOut:
    try:
        preview = preview_import(db, body.text, body.account_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ImportPreviewOut(
        line_count=preview.line_count,
        new_emails=preview.new_emails,
        conflict_emails=preview.conflict_emails,
    )


@router.post("/import", response_model=ImportResultOut)
def import_accounts(body: ImportApplyBody, db: Session = Depends(get_db)) -> ImportResultOut:
    try:
        result = apply_import(
            db,
            body.text,
            body.group_id,
            body.conflict_mode,
            body.wipe_all,
            body.account_type,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ImportResultOut(inserted=result.inserted, updated=result.updated, wiped=result.wiped)


@router.post("/batch/delete", response_model=BatchChangeOut)
def batch_delete(body: AccountIdsBody, db: Session = Depends(get_db)) -> BatchChangeOut:
    try:
        count = batch_delete_accounts(db, body.ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return BatchChangeOut(count=count)


@router.post("/batch/move", response_model=BatchChangeOut)
def batch_move(body: AccountBatchMoveBody, db: Session = Depends(get_db)) -> BatchChangeOut:
    try:
        count = batch_move_accounts(db, body.ids, body.group_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return BatchChangeOut(count=count)


@router.delete("/{account_id}", status_code=204)
def delete_account(account_id: int, db: Session = Depends(get_db)) -> None:
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="账号不存在")
    db.delete(account)
    db.commit()
