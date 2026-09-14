"""账号分类目录接口。"""

from fastapi import APIRouter

from app.account_types import list_account_types
from app.schemas import AccountTypeOut

router = APIRouter(prefix="/api/account-types", tags=["account-types"])


@router.get("", response_model=list[AccountTypeOut])
def get_account_types() -> list[AccountTypeOut]:
    return [
        AccountTypeOut(
            code=item.code,
            label=item.label,
            import_hint=item.import_hint,
            supports_mail=item.supports_mail,
        )
        for item in list_account_types()
    ]
