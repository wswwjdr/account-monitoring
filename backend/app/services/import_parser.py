"""按账号分类解析导入文本。本版仅 Outlook 四段。"""

from collections.abc import Callable
from dataclasses import dataclass

from app.account_types import OUTLOOK_FOUR, require_account_type


FIELD_SEP = "----"


@dataclass(frozen=True)
class ParsedAccount:
    """一行凭证解析结果。"""

    email: str
    password: str
    client_id: str
    refresh_token: str
    line_no: int


def normalize_email(email: str) -> str:
    """邮箱按大小写不敏感比对，统一成小写去空白。"""
    if email is None:
        raise ValueError("邮箱不能为空")
    value = email.strip().lower()
    if not value:
        raise ValueError("邮箱不能为空")
    return value


def split_credential_line(line: str) -> list[str]:
    """按 ---- 或 Tab 拆成字段；分隔符必须明确，否则立即失败。"""
    if FIELD_SEP in line:
        return line.split(FIELD_SEP)
    if "\t" in line:
        return line.split("\t")
    raise ValueError("字段分隔符必须是 Tab 或 ----")


def _parse_outlook_four(text: str) -> list[ParsedAccount]:
    """解析 Outlook 四段文本，任一非法行立即抛错，空结果也视为错误。"""
    if text is None:
        raise ValueError("导入文本不能为空")
    rows: list[ParsedAccount] = []
    for line_no, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line:
            continue
        parts = [part.strip() for part in split_credential_line(line)]
        if len(parts) != 4:
            raise ValueError(f"第 {line_no} 行必须恰好包含 4 个字段，实际为 {len(parts)} 个")
        email, password, client_id, refresh_token = parts
        if not email or not password or not client_id or not refresh_token:
            raise ValueError(f"第 {line_no} 行存在空字段")
        if "@" not in email:
            raise ValueError(f"第 {line_no} 行邮箱格式无效")
        rows.append(
            ParsedAccount(
                email=email.strip(),
                password=password,
                client_id=client_id,
                refresh_token=refresh_token,
                line_no=line_no,
            )
        )
    if not rows:
        raise ValueError("没有可导入的账号")
    return rows


_PARSERS: dict[str, Callable[[str], list[ParsedAccount]]] = {
    OUTLOOK_FOUR: _parse_outlook_four,
}


def parse_import_text(text: str, account_type: str) -> list[ParsedAccount]:
    """按分类解析导入文本；未选分类或没有对应解析器立即失败。"""
    code = require_account_type(account_type)
    parser = _PARSERS.get(code)
    if parser is None:
        raise ValueError("不支持的账号分类")
    return parser(text)
