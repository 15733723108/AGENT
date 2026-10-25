"""知识库文档入库（离线任务）：解析 → 分块 → 向量化 → 业务落库。

业务落库：kb_documents + kb_chunks（先写业务库，再写向量库，vector_id 回填）。
文档废弃（is_active=0）时按 doc_id 删除向量，避免孤儿数据（对齐文档 4.2）。
除文件入库外，还支持粘贴文本直接入库（ingest_text）。
"""
import json
from pathlib import Path

from app.database import SessionLocal
from app.models.entities import KbChunk, KbDocument
from app.services.doc_parser import parse_file
from app.services.rag_pipeline import ChunkRecord, rag_pipeline, split_document
from app.utils.logging_conf import get_logger

logger = get_logger("knowledge_ingest")


def _category_for(path: Path, forced: str = "auto") -> str:
    if forced and forced != "auto":
        return forced
    # 按父目录名作为知识域
    return path.parent.name or "general"


def _ingest(
    doc_name: str,
    category: str,
    file_type: str,
    file_path: str,
    source: str,
    text: str,
    uploader_id: int,
) -> int:
    """落库 + 分块 + 向量化，返回 doc_id；文本为空返回 0。"""
    text = (text or "").strip()
    if not text:
        logger.warning("入库内容为空，跳过: %s", doc_name)
        return 0

    db = SessionLocal()
    try:
        doc = KbDocument(
            doc_name=doc_name,
            category=category,
            file_type=file_type,
            file_path=file_path,
            version=1,
            is_active=1,
            uploader_id=uploader_id,
        )
        db.add(doc)
        db.commit()
        db.refresh(doc)

        docs = split_document(text, source=source, doc_id=doc.id)
        records = []
        chunks = []
        for i, d in enumerate(docs):
            md = dict(d.metadata)
            md.update({"doc_id": doc.id, "chunk_index": i, "category": doc.category, "source": source})
            records.append(ChunkRecord(doc_id=doc.id, chunk_index=i, content=d.page_content, metadata=md))
            chunks.append(
                KbChunk(
                    doc_id=doc.id,
                    chunk_index=i,
                    content=d.page_content,
                    chunk_metadata=json.dumps(md, ensure_ascii=False),
                )
            )
        db.add_all(chunks)
        db.commit()

        # 向量化（失败不阻塞业务落库，记录日志）
        try:
            vector_ids = rag_pipeline.ingest_chunks(records)
            for chunk, vid in zip(chunks, vector_ids):
                chunk.vector_id = vid
            db.commit()
        except Exception as exc:
            logger.error("向量化失败 doc_id=%s: %s", doc.id, exc)

        doc.chunk_count = len(chunks)
        db.commit()
        logger.info("入库完成: %s -> doc_id=%s chunks=%d", doc_name, doc.id, len(chunks))
        return doc.id
    finally:
        db.close()


def ingest_file(path: str, category: str = "auto", uploader_id: int = 1) -> int:
    """入库单个文件，返回 doc_id。"""
    p = Path(path)
    text = parse_file(str(p))
    if not text.strip():
        logger.warning("文件解析为空，跳过: %s", p.name)
        return 0
    return _ingest(
        doc_name=p.name,
        category=_category_for(p, category),
        file_type=p.suffix.lstrip(".").lower() or "txt",
        file_path=str(p),
        source=p.name,
        text=text,
        uploader_id=uploader_id,
    )


def ingest_text(title: str, category: str, text: str, uploader_id: int = 1) -> int:
    """入库一段粘贴文本，返回 doc_id。"""
    name = (title or "").strip() or "粘贴文本"
    return _ingest(
        doc_name=name,
        category=(category or "").strip() or "制度",
        file_type="txt",
        file_path="",
        source=name,
        text=text,
        uploader_id=uploader_id,
    )


def ingest_directory(input_dir: str, category: str = "auto", uploader_id: int = 1) -> int:
    """批量入库目录下所有支持的文件，返回成功文件数。"""
    from app.services.doc_parser import SUPPORTED_EXTENSIONS

    root = Path(input_dir)
    if not root.is_dir():
        raise NotADirectoryError(input_dir)
    count = 0
    for p in sorted(root.rglob("*")):
        if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS:
            try:
                if ingest_file(str(p), category=category, uploader_id=uploader_id):
                    count += 1
            except Exception as exc:
                logger.error("文件入库失败 %s: %s", p, exc)
    return count


def deactivate_document(doc_id: int) -> None:
    """废弃文档：业务库 is_active=0 + 删除向量库数据。"""
    db = SessionLocal()
    try:
        doc = db.query(KbDocument).filter(KbDocument.id == doc_id).first()
        if not doc:
            return
        doc.is_active = 0
        db.query(KbChunk).filter(KbChunk.doc_id == doc_id).update({"is_active": 0})
        db.commit()
        try:
            rag_pipeline.store.delete_by_doc(doc_id)
        except Exception as exc:
            logger.error("删除向量失败 doc_id=%s: %s", doc_id, exc)
        logger.info("文档已废弃: doc_id=%s", doc_id)
    finally:
        db.close()