"""按账号版本拉取 Graph 收件箱与邮件详情。"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import DEFAULT_MESSAGE_TOP, MAX_MESSAGE_TOP
from app.db import get_db
from app.models import Account
from app.schemas import MessageDetail, MessageSummary
from app.services.graph_mail import GraphApiError, get_message, list_messages
from app.services.ms_auth import TokenRefreshError, ensure_access_token

router = APIRouter(prefix="/api/accounts", tags=["mails"])


def _require_account(db: Session, account_id: int) -> Account:
    """按主键取账号，不存在则 404。"""
    account = db.get(Account, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="账号不存在")
    return account


def _token_for(db: Session, account: Account, force: bool = False) -> str:
    """换票失败转为 401，便于前端展示令牌异常。"""
    try:
        return ensure_access_token(db, account, force=force)
    except TokenRefreshError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


def _with_graph_retry(db: Session, account: Account, call):
    """先用缓存令牌调 Graph，401 则强制换票重试一次。"""
    token = _token_for(db, account, force=False)
    try:
        return call(token)
    except GraphApiError as exc:
        if exc.status_code != 401:
            raise HTTPException(status_code=502, detail=str(exc)) from exc
        token = _token_for(db, account, force=True)
        try:
            return call(token)
        except GraphApiError as retry_exc:
            raise HTTPException(status_code=502, detail=str(retry_exc)) from retry_exc


@router.get("/{account_id}/messages", response_model=list[MessageSummary])
def read_messages(
    account_id: int,
    top: int = Query(default=DEFAULT_MESSAGE_TOP, ge=1, le=MAX_MESSAGE_TOP),
    db: Session = Depends(get_db),
) -> list[MessageSummary]:
    account = _require_account(db, account_id)
    return _with_graph_retry(db, account, lambda token: list_messages(token, top))


@router.get("/{account_id}/messages/{message_id:path}", response_model=MessageDetail)
def read_message(
    account_id: int,
    message_id: str,
    db: Session = Depends(get_db),
) -> MessageDetail:
    account = _require_account(db, account_id)
    return _with_graph_retry(db, account, lambda token: get_message(token, message_id))
