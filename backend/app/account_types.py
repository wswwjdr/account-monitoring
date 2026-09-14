"""账号分类目录：决定导入格式与可用能力。本版仅 Outlook 四段。"""

from dataclasses import dataclass


OUTLOOK_FOUR = "outlook_four"


@dataclass(frozen=True)
class AccountTypeSpec:
    """一条系统账号分类：编码、界面名称、导入说明、是否支持读信。"""

    code: str
    label: str
    import_hint: str
    supports_mail: bool


ACCOUNT_TYPES: dict[str, AccountTypeSpec] = {
    OUTLOOK_FOUR: AccountTypeSpec(
        code=OUTLOOK_FOUR,
        label="Outlook 四段",
        import_hint="每行一个账号，四个字段必须完整，用 Tab 或 ---- 分隔：邮箱地址----密码----Client ID----刷新令牌",
        supports_mail=True,
    ),
}


def require_account_type(code: str | None) -> str:
    """校验分类编码；未选或不支持立即失败。"""
    if code is None:
        raise ValueError("请选择账号分类")
    value = str(code).strip()
    if not value:
        raise ValueError("请选择账号分类")
    if value not in ACCOUNT_TYPES:
        raise ValueError("不支持的账号分类")
    return value


def get_account_type(code: str | None) -> AccountTypeSpec:
    """按编码取分类规格。"""
    return ACCOUNT_TYPES[require_account_type(code)]


def list_account_types() -> list[AccountTypeSpec]:
    """返回当前已开放的全部分类，供导入下拉使用。"""
    return list(ACCOUNT_TYPES.values())
