"""创建管理员账号。

用法：
    python scripts/create_admin.py --username admin --password admin123456 --name 系统管理员
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal  # noqa: E402
from app.models.entities import User  # noqa: E402
from app.utils.logging_conf import get_logger  # noqa: E402
from app.utils.security import hash_password  # noqa: E402

logger = get_logger("create_admin")


def main() -> None:
    parser = argparse.ArgumentParser(description="创建管理员账号")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="admin123456")
    parser.add_argument("--name", default="系统管理员")
    parser.add_argument("--phone", default="")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        existed = db.query(User).filter(User.username == args.username).first()
        if existed:
            logger.info("用户已存在: %s (role=%s)", existed.username, existed.role)
            return
        user = User(
            username=args.username,
            password_hash=hash_password(args.password),
            display_name=args.name,
            role="admin",
            phone=args.phone,
            status=1,
            is_approved=1,
        )
        db.add(user)
        db.commit()
        logger.info("管理员创建成功: %s / %s", args.username, args.password)
    finally:
        db.close()


if __name__ == "__main__":
    main()
