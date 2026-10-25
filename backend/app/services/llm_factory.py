"""LLM 统一接入层：API / 本地 vLLM 双模式、模型路由、降级策略。

设计要点（对齐开发文档 2.3）：
- 无论 api 还是 local 模式，均通过 OpenAI 兼容协议（ChatOpenAI）接入；
- 按任务复杂度路由：轻量任务（通用问答改写、分类）用快模型，复杂任务（教案/试卷研判）用强模型；
- 降级：主通道配置为空或探测失败时，按候选列表顺序尝试 fallback / 本地 / API；
- 业务代码不感知具体模型，统一从本工厂取实例。
"""
from typing import Optional

import httpx

from app.config import settings
from app.utils.logging_conf import get_logger

logger = get_logger("llm_factory")


class LLMFactory:
    """LangChain ChatModel 工厂（OpenAI 兼容协议）。"""

    def _candidates(self, task: str) -> list[dict]:
        """按任务组装候选模型配置列表（有序，用于降级）。"""
        heavy = task in ("lesson_plan", "exam")
        primary_model = settings.LLM_MODEL_STRONG if heavy else settings.LLM_MODEL

        if settings.LLM_MODE == "local":
            candidates = [
                {
                    "base_url": settings.VLLM_BASE_URL,
                    "api_key": settings.VLLM_API_KEY,
                    "model": settings.VLLM_MODEL,
                    "mode": "local",
                }
            ]
            if settings.FALLBACK_LLM_BASE_URL and settings.FALLBACK_LLM_API_KEY:
                candidates.append(
                    {
                        "base_url": settings.FALLBACK_LLM_BASE_URL,
                        "api_key": settings.FALLBACK_LLM_API_KEY,
                        "model": settings.FALLBACK_LLM_MODEL or primary_model,
                        "mode": "api",
                    }
                )
            return candidates

        # api 模式：主通道 → 本地 vLLM → 显式 fallback
        candidates = [
            {
                "base_url": settings.LLM_BASE_URL,
                "api_key": settings.LLM_API_KEY,
                "model": primary_model,
                "mode": "api",
            }
        ]
        candidates.append(
            {
                "base_url": settings.VLLM_BASE_URL,
                "api_key": settings.VLLM_API_KEY,
                "model": settings.VLLM_MODEL,
                "mode": "local",
            }
        )
        if settings.FALLBACK_LLM_BASE_URL and settings.FALLBACK_LLM_API_KEY:
            candidates.append(
                {
                    "base_url": settings.FALLBACK_LLM_BASE_URL,
                    "api_key": settings.FALLBACK_LLM_API_KEY,
                    "model": settings.FALLBACK_LLM_MODEL or primary_model,
                    "mode": "api",
                }
            )
        return candidates

    def _probe(self, base_url: str, api_key: str) -> bool:
        """探测 OpenAI 兼容端点是否可用（/v1/models）。"""
        try:
            url = base_url.rstrip("/") + "/models"
            headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
            resp = httpx.get(url, headers=headers, timeout=5)
            return resp.status_code < 500
        except Exception:
            return False

    def get_chat_model(self, task: str = "general", stream: bool = True):
        """返回可用 ChatModel 实例。主通道不可用时自动降级。"""
        from langchain_openai import ChatOpenAI

        candidates = self._candidates(task)
        last_err: Optional[Exception] = None
        for cand in candidates:
            if not cand["api_key"]:
                continue
            # 仅对 api 模式主通道做探测；local 模式交给请求时重试
            if cand["mode"] == "api" and cand["base_url"].startswith("https://"):
                if not self._probe(cand["base_url"], cand["api_key"]):
                    last_err = RuntimeError(f"LLM 端点不可用: {cand['base_url']}")
                    continue
            try:
                model = ChatOpenAI(
                    model=cand["model"],
                    base_url=cand["base_url"],
                    api_key=cand["api_key"],
                    temperature=settings.LLM_TEMPERATURE,
                    streaming=stream,
                    timeout=60,
                    max_retries=1,
                )
                logger.info("LLM 路由: task=%s mode=%s model=%s", task, cand["mode"], cand["model"])
                return model
            except Exception as exc:  # pragma: no cover
                last_err = exc
                logger.warning("LLM 初始化失败: %s", exc)
        raise RuntimeError("未配置可用的 LLM（请在 .env 中设置 LLM_API_KEY 或启用本地 vLLM）") from last_err

    def get_embeddings(self):
        """Embedding 模型：优先 API Embedding，其次本地 sentence-transformers。"""
        if settings.EMBEDDING_API_BASE:
            from langchain_openai import OpenAIEmbeddings

            return OpenAIEmbeddings(
                model=settings.EMBEDDING_MODEL,
                api_key=settings.EMBEDDING_API_KEY or settings.LLM_API_KEY,
                base_url=settings.EMBEDDING_API_BASE,
            )
        try:
            from langchain_huggingface import HuggingFaceEmbeddings

            logger.info("使用本地 Embedding: %s", settings.EMBEDDING_MODEL)
            return HuggingFaceEmbeddings(model_name=settings.EMBEDDING_MODEL)
        except Exception as exc:
            raise RuntimeError(
                "未配置 Embedding：请设置 EMBEDDING_API_BASE 或安装 sentence-transformers"
            ) from exc


llm_factory = LLMFactory()
