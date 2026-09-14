"""SQLite 引擎、会话工厂与启动时补齐表结构。"""

from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import DATA_DIR, DB_PATH, LEGACY_DEFAULT_GROUP_NAME

DATA_DIR.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    f"sqlite:///{DB_PATH.as_posix()}",
    connect_args={"check_same_thread": False},
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """向请求注入数据库会话，结束时关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _pragma_columns(table_name: str) -> list[tuple]:
    """读取 SQLite 表结构行。"""
    with engine.connect() as conn:
        return list(conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall())


def _table_columns(table_name: str) -> set[str]:
    """读取 SQLite 表的列名集合。"""
    return {row[1] for row in _pragma_columns(table_name)}


def _column_notnull(table_name: str, column_name: str) -> bool:
    """判断某列是否为 NOT NULL。"""
    for row in _pragma_columns(table_name):
        if row[1] == column_name:
            return bool(row[3])
    return False


def _retire_legacy_default_group() -> None:
    """去掉历史上的默认分组，其账号改为未分组。"""
    group_cols = _table_columns("groups")
    if not group_cols:
        return
    with engine.begin() as conn:
        ids: set[int] = set()
        named = conn.execute(
            text("SELECT id FROM groups WHERE name = :name"),
            {"name": LEGACY_DEFAULT_GROUP_NAME},
        ).fetchall()
        ids.update(int(row[0]) for row in named)
        if "is_default" in group_cols:
            flagged = conn.execute(text("SELECT id FROM groups WHERE is_default = 1")).fetchall()
            ids.update(int(row[0]) for row in flagged)
        if ids:
            placeholders = ",".join(str(item) for item in ids)
            conn.execute(text(f"UPDATE accounts SET group_id = NULL WHERE group_id IN ({placeholders})"))
            conn.execute(text(f"DELETE FROM groups WHERE id IN ({placeholders})"))
        if "is_default" in group_cols:
            conn.execute(text("ALTER TABLE groups DROP COLUMN is_default"))


def _rebuild_accounts_nullable_group() -> None:
    """重建 accounts 表，使 group_id 可空。"""
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE accounts_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    group_id INTEGER,
                    email VARCHAR(320) NOT NULL,
                    password VARCHAR(512) NOT NULL,
                    client_id VARCHAR(64) NOT NULL,
                    refresh_token TEXT NOT NULL,
                    imported_at DATETIME NOT NULL,
                    access_token TEXT,
                    token_expires_at DATETIME,
                    token_status VARCHAR(16) NOT NULL,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL,
                    FOREIGN KEY(group_id) REFERENCES groups (id)
                )
                """
            )
        )
        conn.execute(
            text(
                """
                INSERT INTO accounts_new (
                    id, group_id, email, password, client_id, refresh_token,
                    imported_at, access_token, token_expires_at, token_status,
                    created_at, updated_at
                )
                SELECT
                    id, group_id, email, password, client_id, refresh_token,
                    imported_at, access_token, token_expires_at, token_status,
                    created_at, updated_at
                FROM accounts
                """
            )
        )
        conn.execute(text("DROP TABLE accounts"))
        conn.execute(text("ALTER TABLE accounts_new RENAME TO accounts"))
        conn.execute(text("CREATE INDEX ix_accounts_email ON accounts (email)"))
        conn.execute(text("CREATE INDEX ix_accounts_group_id ON accounts (group_id)"))


def _ensure_account_columns() -> None:
    """为旧库补上令牌说明与换票入口列。"""
    columns = _table_columns("accounts")
    with engine.begin() as conn:
        if "token_error" not in columns:
            conn.execute(text("ALTER TABLE accounts ADD COLUMN token_error TEXT"))
        if "token_endpoint" not in columns:
            conn.execute(text("ALTER TABLE accounts ADD COLUMN token_endpoint VARCHAR(160)"))


def ensure_schema() -> None:
    """创建缺表，补齐 group_id，并清除旧的默认分组。"""
    from app.models import Account

    Base.metadata.create_all(bind=engine)
    if "group_id" not in _table_columns(Account.__tablename__):
        with engine.begin() as conn:
            conn.execute(text(f"ALTER TABLE {Account.__tablename__} ADD COLUMN group_id INTEGER"))
    _retire_legacy_default_group()
    if _column_notnull(Account.__tablename__, "group_id"):
        _rebuild_accounts_nullable_group()
    _ensure_account_columns()
