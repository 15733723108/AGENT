"""RAG 检索链路（对齐开发文档 2.4）：分块 → 向量化 → 混合检索 → RRF 融合 → 可选重排。

向量后端支持三种（VECTOR_BACKEND）：
- milvus  ：生产推荐，Milvus 2.4+（HNSW/COSINE）
- pgvector：轻量替代，PostgreSQL + pgvector 插件
- memory  ：进程内内存检索（关键词/ngram 打分），无需外部组件，便于本地直接运行
"""
import math
import re
from dataclasses import dataclass, field
from typing import Optional

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.utils.logging_conf import get_logger

logger = get_logger("rag")


@dataclass
class ChunkRecord:
    doc_id: int
    chunk_index: int
    content: str
    metadata: dict = field(default_factory=dict)


@dataclass
class SearchHit:
    content: str
    metadata: dict
    score: float


def split_document(text: str, source: str = "", doc_id: int = 0) -> list[Document]:
    """按标题层级 + 固定大小分块（块大小 600，重叠 80，可配置）。"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.RAG_CHUNK_SIZE,
        chunk_overlap=settings.RAG_CHUNK_OVERLAP,
        separators=["\n## ", "\n### ", "\n# ", "\n\n", "\n", "。", " ", ""],
    )
    docs = splitter.create_documents([text], metadatas=[{"source": source, "doc_id": doc_id}])
    return docs


def _tokenize(text: str) -> set[str]:
    """简易中英文分词：中文连续串 + 英文单词。"""
    tokens = set(re.findall(r"[a-zA-Z0-9_]+", text.lower()))
    tokens |= set(re.findall(r"[\u4e00-\u9fa5]{2,}", text))
    return tokens


def _bigrams(text: str) -> set[str]:
    cleaned = re.sub(r"\s+", "", text)
    return {cleaned[i : i + 2] for i in range(len(cleaned) - 1)}


# ============ 向量存储抽象 ============


class BaseVectorStore:
    """向量存储抽象接口。"""

    def add_chunks(self, records: list[ChunkRecord]) -> list[str]:
        raise NotImplementedError

    def search(self, query: str, top_k: int, category: Optional[str] = None) -> list[SearchHit]:
        raise NotImplementedError

    def keyword_search(self, query: str, top_k: int, category: Optional[str] = None) -> list[SearchHit]:
        raise NotImplementedError

    def delete_by_doc(self, doc_id: int) -> None:
        raise NotImplementedError


class MemoryVectorStore(BaseVectorStore):
    """内存检索：bigram Dice + 关键词命中率加权，无需 Embedding 模型。"""

    def __init__(self):
        self._chunks: list[ChunkRecord] = []

    def add_chunks(self, records: list[ChunkRecord]) -> list[str]:
        ids = []
        for r in records:
            self._chunks.append(r)
            ids.append(str(r.doc_id) + "_" + str(r.chunk_index))
        logger.info("memory store 新增 %d 块", len(records))
        return ids

    def _score(self, query: str, content: str) -> float:
        q_bigrams, c_bigrams = _bigrams(query), _bigrams(content)
        if not q_bigrams or not c_bigrams:
            return 0.0
        inter = len(q_bigrams & c_bigrams)
        dice = 2.0 * inter / (len(q_bigrams) + len(c_bigrams) + 1e-9)
        q_tokens = _tokenize(query)
        c_tokens = _tokenize(content)
        hit = len(q_tokens & c_tokens) / (len(q_tokens) + 1e-9)
        return 0.7 * dice + 0.3 * hit

    def _candidates(self, query: str, top_k: int, category: Optional[str]):
        scored = [
            (r, self._score(query, r.content))
            for r in self._chunks
            if (category is None or r.metadata.get("category") == category)
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]

    def search(self, query, top_k, category=None):
        return [
            SearchHit(content=r.content, metadata=r.metadata, score=s)
            for r, s in self._candidates(query, top_k, category)
        ]

    def keyword_search(self, query, top_k, category=None):
        return self.search(query, top_k, category)

    def delete_by_doc(self, doc_id: int) -> None:
        self._chunks = [r for r in self._chunks if r.doc_id != doc_id]


class MilvusVectorStore(BaseVectorStore):
    """Milvus 向量检索（pymilvus 直连，需先 init_vector_db.py 建 collection）。"""

    def __init__(self, embeddings):
        try:
            from pymilvus import Collection, connections
        except ImportError as exc:
            raise RuntimeError("VECTOR_BACKEND=milvus 需要安装 pymilvus") from exc
        self.embeddings = embeddings
        connections.connect(alias="default", host=settings.MILVUS_HOST, port=settings.MILVUS_PORT)
        self.collection = Collection(settings.MILVUS_COLLECTION)
        self.collection.load()

    def add_chunks(self, records: list[ChunkRecord]) -> list[str]:
        vectors = self.embeddings.embed_documents([r.content for r in records])
        rows = [
            {
                "chunk_id": r.chunk_index,
                "doc_id": r.doc_id,
                "category": r.metadata.get("category", ""),
                "source": r.metadata.get("source", ""),
                "content": r.content,
                "vector": vec,
            }
            for r, vec in zip(records, vectors)
        ]
        self.collection.insert(rows)
        self.collection.flush()
        return [str(r.doc_id) + "_" + str(r.chunk_index) for r in records]

    def _search(self, query, top_k, category, is_keyword):
        expr = f'category == "{category}"' if category else None
        if is_keyword:
            # 关键词检索：以检索到的文本再次嵌入近邻，简化实现（生产建议接 ES/MySQL 全文）
            q_emb = self.embeddings.embed_query(query)
        else:
            q_emb = self.embeddings.embed_query(query)
        results = self.collection.search(
            data=[q_emb],
            anns_field="vector",
            param={"metric_type": "COSINE", "params": {"ef": 64}},
            limit=top_k,
            expr=expr,
            output_fields=["content", "doc_id", "category", "source", "chunk_id"],
        )
        hits = []
        for res in results[0]:
            hits.append(
                SearchHit(
                    content=res.entity.get("content"),
                    metadata={
                        "doc_id": res.entity.get("doc_id"),
                        "chunk_id": res.entity.get("chunk_id"),
                        "category": res.entity.get("category"),
                        "source": res.entity.get("source"),
                    },
                    score=float(res.distance),
                )
            )
        return hits

    def search(self, query, top_k, category=None):
        return self._search(query, top_k, category, is_keyword=False)

    def keyword_search(self, query, top_k, category=None):
        return self._search(query, top_k, category, is_keyword=True)

    def delete_by_doc(self, doc_id: int) -> None:
        self.collection.delete(f"doc_id in [{doc_id}]")
        self.collection.flush()


class PGVectorStore(BaseVectorStore):
    """pgvector 向量检索（langchain-postgres）。"""

    def __init__(self, embeddings):
        try:
            from langchain_postgres import PGVector
        except ImportError as exc:
            raise RuntimeError("VECTOR_BACKEND=pgvector 需要安装 langchain-postgres 与 psycopg") from exc
        self.embeddings = embeddings
        self.store = PGVector(
            embeddings=embeddings,
            collection_name=settings.MILVUS_COLLECTION,
            connection=settings.PGVECTOR_CONNECTION_STRING,
        )

    def add_chunks(self, records: list[ChunkRecord]) -> list[str]:
        docs = [
            Document(
                page_content=r.content,
                metadata={**r.metadata, "doc_id": r.doc_id, "chunk_id": r.chunk_index},
            )
            for r in records
        ]
        self.store.add_documents(docs)
        return [str(r.doc_id) + "_" + str(r.chunk_index) for r in records]

    def _run(self, query, top_k, category, is_keyword):
        q = query if is_keyword else query
        docs = self.store.similarity_search_with_score(q, k=top_k)
        hits = []
        for doc, score in docs:
            md = doc.metadata
            if category and md.get("category") != category:
                continue
            hits.append(SearchHit(content=doc.page_content, metadata=md, score=float(score)))
        return hits

    def search(self, query, top_k, category=None):
        return self._run(query, top_k, category, is_keyword=False)

    def keyword_search(self, query, top_k, category=None):
        return self._run(query, top_k, category, is_keyword=True)

    def delete_by_doc(self, doc_id: int) -> None:
        self.store.delete(filter={"doc_id": {"$eq": doc_id}})


def _rrf_merge(list_a: list[SearchHit], list_b: list[SearchHit], k: int = 60) -> list[SearchHit]:
    """Reciprocal Rank Fusion 融合排序。"""
    scores: dict[str, float] = {}
    by_key: dict[str, SearchHit] = {}
    for rank, hit in enumerate(list_a + list_b):
        key = (hit.metadata.get("doc_id"), hit.metadata.get("chunk_id"), hit.content[:80])
        key = str(key)
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
        by_key[key] = hit
    merged = sorted(by_key.items(), key=lambda kv: scores[kv[0]], reverse=True)
    return [hit for _, hit in merged]


class RAGPipeline:
    """RAG 管道：入库 + 混合检索 + RRF + 可选重排。"""

    def __init__(self):
        self.backend = settings.VECTOR_BACKEND
        if self.backend == "memory":
            self.store = MemoryVectorStore()
        elif self.backend == "milvus":
            from app.services.llm_factory import llm_factory

            self.store = MilvusVectorStore(llm_factory.get_embeddings())
        elif self.backend == "pgvector":
            from app.services.llm_factory import llm_factory

            self.store = PGVectorStore(llm_factory.get_embeddings())
        else:
            raise RuntimeError(f"未知 VECTOR_BACKEND: {self.backend}")
        logger.info("RAG 后端: %s", self.backend)

    def ingest_chunks(self, records: list[ChunkRecord]) -> list[str]:
        """写入向量库，返回 vector_id 列表。"""
        return self.store.add_chunks(records)

    def search(self, query: str, category: Optional[str] = None) -> list[SearchHit]:
        top_k = settings.RAG_TOP_K
        vector_hits = self.store.search(query, top_k, category)
        keyword_hits = self.store.keyword_search(query, top_k, category)
        merged = _rrf_merge(vector_hits, keyword_hits)
        final_k = settings.RAG_FINAL_K
        reranked = self._try_rerank(query, merged[: final_k * 2]) if self.backend != "memory" else merged
        return reranked[:final_k]

    def _try_rerank(self, query: str, hits: list[SearchHit]) -> list[SearchHit]:
        """使用 bge-reranker（如已安装）精排，否则原序。"""
        try:
            from sentence_transformers import CrossEncoder

            model = CrossEncoder(settings.RERANK_MODEL)
            pairs = [[query, h.content[:400]] for h in hits]
            scores = model.predict(pairs)
            ranked = sorted(zip(hits, scores), key=lambda x: x[1], reverse=True)
            logger.info("rerank 完成 top=%d", len(ranked))
            return [h for h, _ in ranked]
        except Exception:
            return hits

    def format_context(self, hits: list[SearchHit]) -> str:
        """组装 Prompt 参考资料（带 [N] 编号与来源）。"""
        parts = []
        for i, hit in enumerate(hits, start=1):
            source = hit.metadata.get("source", "未知来源")
            parts.append(f"[{i}] (来源: {source})\n{hit.content[:600]}")
        return "\n\n".join(parts)


rag_pipeline = RAGPipeline()
