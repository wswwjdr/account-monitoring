"""应用级常量：本地绑定、数据库路径、微软鉴权与 Graph 端点。"""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "app.db"

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
LEGACY_DEFAULT_GROUP_NAME = "默认分组"
