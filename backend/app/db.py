"""PostgreSQL 引擎、会话工厂与启动时建表。"""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import DATABASE_URL

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """向请求注入数据库会话，结束时关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_schema() -> None:
    """按模型创建缺失的表。"""
    from app.models import Account, Group

    Base.metadata.create_all(bind=engine, tables=[Group.__table__, Account.__table__])
