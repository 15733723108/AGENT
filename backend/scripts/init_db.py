"""初始化数据库：建表 + 写入初始管理员账号。

用法：python scripts/init_db.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import Base, engine  # noqa: E402
from app.models import entities  # noqa: F401, E402  # 确保模型注册
from app.utils.logging_conf import get_logger

logger = get_logger("init_db")


def _ensure_approval_column() -> None:
    """为已存在的 users 表补充 is_approved 列（轻量迁移，create_all 不会变更已有表）。"""
    from sqlalchemy import inspect, text

    insp = inspect(engine)
    if "users" not in insp.get_table_names():
        return
    cols = [c["name"] for c in insp.get_columns("users")]
    if "is_approved" in cols:
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE users ADD COLUMN is_approved TINYINT NOT NULL DEFAULT 1"))
    logger.info("已为 users 表补充 is_approved 列")


def main() -> None:
    logger.info("开始创建数据表...")
    Base.metadata.create_all(bind=engine)
    _ensure_approval_column()
    logger.info("数据表创建完成（users/chat_sessions/chat_messages/kb_documents/kb_chunks/lesson_plans/exams/exam_questions/exam_reports/llm_usage）")


if __name__ == "__main__":
    main()
