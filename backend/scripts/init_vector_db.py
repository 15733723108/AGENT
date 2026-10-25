"""初始化向量库 Collection（Milvus）。

用法：python scripts/init_vector_db.py
- VECTOR_BACKEND=memory 时打印跳过提示；
- VECTOR_BACKEND=milvus 时创建 collection + HNSW 索引；
- VECTOR_BACKEND=pgvector 时提示在 PostgreSQL 中执行 CREATE EXTENSION vector。
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402
from app.utils.logging_conf import get_logger  # noqa: E402

logger = get_logger("init_vector_db")


def init_milvus() -> None:
    from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

    connections.connect(alias="default", host=settings.MILVUS_HOST, port=settings.MILVUS_PORT)
    name = settings.MILVUS_COLLECTION
    if utility.has_collection(name):
        logger.info("collection 已存在: %s", name)
        return
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
        FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=settings.EMBEDDING_DIM),
        FieldSchema(name="chunk_id", dtype=DataType.INT64),
        FieldSchema(name="doc_id", dtype=DataType.INT64),
        FieldSchema(name="category", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=255),
        FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
    ]
    schema = CollectionSchema(fields=fields, description="school agent kb", enable_dynamic_field=False)
    col = Collection(name=name, schema=schema)
    index_params = {
        "index_type": "HNSW",
        "metric_type": "COSINE",
        "params": {"M": 16, "efConstruction": 200},
    }
    col.create_index(field_name="vector", index_params=index_params)
    logger.info("collection 创建完成: %s (dim=%d)", name, settings.EMBEDDING_DIM)


def main() -> None:
    if settings.VECTOR_BACKEND == "memory":
        logger.info("VECTOR_BACKEND=memory，无需向量库初始化。")
    elif settings.VECTOR_BACKEND == "milvus":
        init_milvus()
    elif settings.VECTOR_BACKEND == "pgvector":
        logger.info("pgvector 初始化请在 PostgreSQL 中执行：CREATE EXTENSION IF NOT EXISTS vector; 并创建 schema（见 README）。")


if __name__ == "__main__":
    main()
