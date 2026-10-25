"""知识库批量导入 CLI。

用法：
    python scripts/ingest_kb.py --dir ./kb_docs                    # 批量导入目录
    python scripts/ingest_kb.py --file ./kb_docs/招生简章.pdf       # 导入单个文件
    python scripts/ingest_kb.py --dir ./kb_docs --category 招生     # 指定知识域
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.knowledge.ingest import ingest_directory, ingest_file  # noqa: E402
from app.utils.logging_conf import get_logger  # noqa: E402

logger = get_logger("ingest_kb")


def main() -> None:
    parser = argparse.ArgumentParser(description="知识库文档导入")
    parser.add_argument("--dir", default="", help="待导入目录（递归扫描支持的文件）")
    parser.add_argument("--file", default="", help="待导入的单个文件")
    parser.add_argument("--category", default="auto", help="知识域（auto=按目录名推断）")
    parser.add_argument("--uploader-id", type=int, default=1, help="上传人 user_id")
    args = parser.parse_args()

    if args.file:
        path = Path(args.file)
        if not path.is_file():
            logger.error("文件不存在: %s", args.file)
            sys.exit(1)
        doc_id = ingest_file(str(path), category=args.category, uploader_id=args.uploader_id)
        logger.info("导入完成 doc_id=%s", doc_id)
    elif args.dir:
        root = Path(args.dir)
        if not root.is_dir():
            logger.error("目录不存在: %s", args.dir)
            sys.exit(1)
        count = ingest_directory(str(root), category=args.category, uploader_id=args.uploader_id)
        logger.info("批量导入完成，成功 %d 个文件", count)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
