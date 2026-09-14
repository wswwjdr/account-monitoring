"""HTTP 请求与响应模型。"""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class GroupOut(BaseModel):
    id: int
    name: str
    account_count: int
    created_at: datetime
    updated_at: datetime


class GroupWriteBody(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class AccountOut(BaseModel):
    id: int
    group_id: int | None
    group_name: str
    email: str
    password: str
    client_id: str
    imported_at: datetime
    token_status: str
    token_error: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ImportTextBody(BaseModel):
    text: str = Field(min_length=1)


class ImportApplyBody(BaseModel):
    text: str = Field(min_length=1)
    group_id: int | None = None
    conflict_mode: Literal["append", "replace_latest"] | None = None
    wipe_all: bool = False


class ImportPreviewOut(BaseModel):
    line_count: int
    new_emails: list[str]
    conflict_emails: list[str]


class ImportResultOut(BaseModel):
    inserted: int
    updated: int
    wiped: bool


class AccountIdsBody(BaseModel):
    ids: list[int] = Field(min_length=1)


class AccountBatchMoveBody(BaseModel):
    ids: list[int] = Field(min_length=1)
    group_id: int | None = None


class BatchChangeOut(BaseModel):
    count: int


class MessageSummary(BaseModel):
    id: str
    subject: str | None
    from_name: str | None
    from_address: str | None
    received_at: str | None
    is_read: bool
    preview: str | None


class MessageDetail(MessageSummary):
    body_content: str
    body_type: str
