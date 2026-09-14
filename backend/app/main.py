"""本地账号管家 API 入口：仅绑定本机，供前端开发服务器代理。"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db import ensure_schema
from app.routers import accounts, groups, mails

ensure_schema()

app = FastAPI(title="账号管家", docs_url=None, redoc_url=None)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(accounts.router)
app.include_router(groups.router)
app.include_router(mails.router)


@app.get("/")
def root() -> dict[str, str]:
    """浏览器直接打开 8787 时的提示，避免根路径 404 刷日志。"""
    return {
        "service": "账号管家",
        "health": "/api/health",
        "frontend": "http://127.0.0.1:5173",
    }


@app.get("/json/version")
def chrome_devtools_probe() -> dict[str, str]:
    """Cursor/Chrome 会探测 CDP 版本接口；返回空对象，避免 404。"""
    return {}


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
