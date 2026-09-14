"""应用级常量：本地绑定、数据库连接、微软鉴权与 Graph 端点。"""

import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

_BACKEND_DIR = Path(__file__).resolve().parents[1]
load_dotenv(_BACKEND_DIR / ".env")


def _require(name: str) -> str:
    """读取必填配置；缺项或空值立即失败。"""
    value = os.environ.get(name)
    if value is None or not str(value).strip():
        raise RuntimeError(f"缺少配置 {name}，请复制 backend/.env.example 为 backend/.env 并填写。")
    return str(value).strip()


DB_HOST = _require("DB_HOST")
DB_PORT = _require("DB_PORT")
DB_NAME = _require("DB_NAME")
DB_USER = _require("DB_USER")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
if DB_PASSWORD is None:
    raise RuntimeError("缺少配置 DB_PASSWORD，请复制 backend/.env.example 为 backend/.env 并填写。")

DATABASE_URL = (
    f"postgresql+psycopg://{quote_plus(DB_USER)}:{quote_plus(DB_PASSWORD)}"
    f"@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

API_HOST = "127.0.0.1"
API_PORT = 8787

TOKEN_URLS = (
    "https://login.microsoftonline.com/common/oauth2/v2.0/token",
    "https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
    "https://login.microsoftonline.com/organizations/oauth2/v2.0/token",
)
GRAPH_BASE = "https://graph.microsoft.com/v1.0"
GRAPH_SCOPE = "https://graph.microsoft.com/Mail.Read offline_access openid profile"

TOKEN_REFRESH_SKEW_SECONDS = 120
HTTP_TIMEOUT_SECONDS = 30.0
DEFAULT_MESSAGE_TOP = 50
MAX_MESSAGE_TOP = 100
UNGROUPED_LABEL = "未分组"
