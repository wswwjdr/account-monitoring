"""调用 Microsoft Graph 拉取收件箱列表与邮件详情。"""

from typing import Any

import httpx

from app.config import GRAPH_BASE, HTTP_TIMEOUT_SECONDS
from app.schemas import MessageDetail, MessageSummary


class GraphApiError(Exception):
    """Graph 接口失败。"""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _graph_error_message(response: httpx.Response) -> str:
    """从 Graph 错误响应提取可读说明。"""
    try:
        payload = response.json()
    except ValueError:
        return response.text
    error = payload.get("error") if isinstance(payload, dict) else None
    if isinstance(error, dict):
        return str(error.get("message") or error.get("code") or payload)
    return str(payload)


def _sender_fields(item: dict[str, Any]) -> tuple[str | None, str | None]:
    """从 Graph message.from 取出显示名与地址。"""
    sender = (item.get("from") or {}).get("emailAddress") or {}
    name = sender.get("name")
    address = sender.get("address")
    return (str(name) if name else None, str(address) if address else None)


def _to_summary(item: dict[str, Any]) -> MessageSummary:
    """把 Graph 列表项映射成摘要模型。"""
    message_id = item.get("id")
    if not message_id:
        raise GraphApiError("邮件响应缺少 id")
    from_name, from_address = _sender_fields(item)
    return MessageSummary(
        id=str(message_id),
        subject=item.get("subject"),
        from_name=from_name,
        from_address=from_address,
        received_at=item.get("receivedDateTime"),
        is_read=bool(item.get("isRead")),
        preview=item.get("bodyPreview"),
    )


def graph_get(access_token: str, path: str, params: dict[str, Any] | None = None) -> httpx.Response:
    """带 Bearer 访问 Graph，不在此层吞错。"""
    url = f"{GRAPH_BASE}{path}"
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        return httpx.get(url, headers=headers, params=params, timeout=HTTP_TIMEOUT_SECONDS)
    except httpx.HTTPError as exc:
        raise GraphApiError(f"Graph 请求失败：{exc}") from exc


def list_messages(access_token: str, top: int) -> list[MessageSummary]:
    """按收件时间倒序取收件箱摘要。"""
    if top < 1:
        raise ValueError("top 必须大于 0")
    params = {
        "$top": str(top),
        "$select": "id,subject,from,receivedDateTime,isRead,bodyPreview",
        "$orderby": "receivedDateTime desc",
    }
    response = graph_get(access_token, "/me/messages", params)
    if response.status_code != 200:
        raise GraphApiError(_graph_error_message(response), response.status_code)
    payload = response.json()
    items = payload.get("value")
    if not isinstance(items, list):
        raise GraphApiError("邮件列表响应缺少 value")
    return [_to_summary(item) for item in items]


def get_message(access_token: str, message_id: str) -> MessageDetail:
    """读取单封邮件正文。"""
    if not message_id:
        raise ValueError("message_id 不能为空")
    params = {
        "$select": "id,subject,from,receivedDateTime,isRead,bodyPreview,body",
    }
    response = graph_get(access_token, f"/me/messages/{message_id}", params)
    if response.status_code != 200:
        raise GraphApiError(_graph_error_message(response), response.status_code)
    item = response.json()
    summary = _to_summary(item)
    body = item.get("body") or {}
    content = body.get("content")
    content_type = body.get("contentType") or "text"
    return MessageDetail(
        **summary.model_dump(),
        body_content=content if isinstance(content, str) else "",
        body_type=str(content_type).lower(),
    )
