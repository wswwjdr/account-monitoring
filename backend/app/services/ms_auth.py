"""用 Refresh Token 向微软换取 Access Token。"""

from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy.orm import Session

from app.config import GRAPH_SCOPE, HTTP_TIMEOUT_SECONDS, TOKEN_REFRESH_SKEW_SECONDS, TOKEN_URLS
from app.models import Account, utc_now


class TokenRefreshError(Exception):
    """刷新令牌失败，调用方应标记账号令牌异常。"""


def _as_utc(value: datetime | None) -> datetime | None:
    """把可能被 SQLite 读成 naive 的时间统一成 UTC。"""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def access_token_still_valid(account: Account) -> bool:
    """判断缓存的 access_token 是否仍可在偏移窗口内使用。"""
    if not account.access_token:
        return False
    expires_at = _as_utc(account.token_expires_at)
    if expires_at is None:
        return False
    return expires_at > utc_now() + timedelta(seconds=TOKEN_REFRESH_SKEW_SECONDS)


def compact_token_error(raw: str) -> str:
    """去掉 Trace / Correlation 等噪音，保留错误码与主说明。"""
    if raw is None:
        raise ValueError("错误信息不能为空")
    text = raw.strip()
    for marker in ("Trace ID:", "Correlation ID:", "Timestamp:"):
        index = text.find(marker)
        if index != -1:
            text = text[:index]
    text = " ".join(text.split())
    if "AADSTS7000012" in text:
        return "刷新令牌与换票租户不一致（AADSTS7000012）。已尝试通用入口与个人/组织入口，仍失败。请重新授权后导入。"
    if "AADSTS70000" in text or "invalid_grant" in text:
        return "刷新令牌已失效或已被吊销，请重新获取四段凭证后导入。"
    if not text:
        return "换票失败，原因未知。"
    return text


def _token_endpoints(account: Account) -> list[str]:
    """上次成功的入口优先，再尝试其余微软入口。"""
    ordered: list[str] = []
    preferred = (account.token_endpoint or "").strip()
    if preferred:
        ordered.append(preferred)
    for url in TOKEN_URLS:
        if url not in ordered:
            ordered.append(url)
    return ordered


def _read_json(response: httpx.Response) -> dict:
    """读取换票响应 JSON；非 JSON 则空字典。"""
    try:
        payload = response.json()
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _post_refresh(account: Account, token_url: str) -> httpx.Response:
    """向指定入口提交 refresh_token。"""
    form = {
        "client_id": account.client_id,
        "grant_type": "refresh_token",
        "refresh_token": account.refresh_token,
        "scope": GRAPH_SCOPE,
    }
    return httpx.post(token_url, data=form, timeout=HTTP_TIMEOUT_SECONDS)


def refresh_access_token(account: Account) -> None:
    """依次尝试微软换票入口并写回账号；全部失败则抛 TokenRefreshError。"""
    if not account.client_id:
        raise TokenRefreshError("Client ID 为空")
    if not account.refresh_token:
        raise TokenRefreshError("刷新令牌为空")

    last_error = "换票失败"
    for token_url in _token_endpoints(account):
        try:
            response = _post_refresh(account, token_url)
        except httpx.HTTPError as exc:
            last_error = f"换票请求失败：{exc}"
            continue
        payload = _read_json(response)
        if response.status_code != 200:
            last_error = str(payload.get("error_description") or payload.get("error") or response.text)
            continue
        access_token = payload.get("access_token")
        if not access_token:
            last_error = "换票响应缺少 access_token"
            continue
        now = utc_now()
        expires_in = int(payload.get("expires_in") or 3600)
        account.access_token = access_token
        account.token_expires_at = now + timedelta(seconds=expires_in)
        rotated = payload.get("refresh_token")
        if rotated:
            account.refresh_token = rotated
        account.token_status = "normal"
        account.token_error = None
        account.token_endpoint = token_url
        account.updated_at = now
        return
    raise TokenRefreshError(compact_token_error(last_error))


def ensure_access_token(db: Session, account: Account, force: bool = False) -> str:
    """保证账号持有可用 access_token；必要时换票并落库。"""
    if not force and access_token_still_valid(account):
        return account.access_token
    try:
        refresh_access_token(account)
    except TokenRefreshError as exc:
        account.token_status = "error"
        account.token_error = str(exc)
        account.access_token = None
        account.token_expires_at = None
        account.updated_at = utc_now()
        db.commit()
        raise
    db.commit()
    db.refresh(account)
    if not account.access_token:
        raise TokenRefreshError("换票后仍无 access_token")
    return account.access_token
