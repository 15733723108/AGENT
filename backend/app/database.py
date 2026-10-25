"""SQLAlchemy 引擎与会话管理。

数据库选择优先级：
1. 若设置 DATABASE_URL（如 MySQL/PostgreSQL 完整连接串），优先使用；
2. 否则按 MYSQL_* 逐项配置拼接 MySQL 连接串；
3. 若 MYSQL_HOST 为空或连接失败（本地无 MySQL），自动回退 SQLite，保证开箱即用。
"""
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings


def _build_url() -> str:
    if settings.DATABASE_URL:
        return settings.DATABASE_URL
    if settings.MYSQL_HOST:
        return settings.mysql_url
    # SQLite 兜底（本地开发 / 演示）
    data_dir = Path(__file__).resolve().parents[1] / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{(data_dir / 'school_agent.db').as_posix()}"


DATABASE_URL = _build_url()
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
    connect_args=connect_args,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    """FastAPI 依赖：请求级数据库会话。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
