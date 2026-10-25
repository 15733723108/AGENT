"""学校信息问答服务：强制 RAG、防幻觉约束、引用标记后处理、流式输出。

对齐开发文档 3.3：仅依据知识库资料回答，输出 [N] 引用标记；
低置信度/检索为空时返回"知识库暂未收录"兜底话术。
"""
import re
from typing import AsyncGenerator, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from app.prompts import templates
from app.services.llm_factory import llm_factory
from app.services.rag_pipeline import rag_pipeline
from app.services.session_manager import build_context_messages, history_to_lc_messages
from app.utils.logging_conf import get_logger

logger = get_logger("school_info_service")

NOT_FOUND_TEXT = "该问题知识库暂未收录，建议咨询学校教务处（电话详见官网）。"


def _parse_refs(answer: str, hits) -> list[dict]:
    """解析回答中的 [N] 引用标记，关联检索命中的来源元数据。"""
    refs = []
    seen = set()
    for m in re.finditer(r"\[(\d+)\]", answer):
        idx = int(m.group(1))
        if idx in seen or idx < 1 or idx > len(hits):
            continue
        seen.add(idx)
        hit = hits[idx - 1]
        md = hit.metadata
        refs.append(
            {
                "index": idx,
                "source": md.get("source", "未知来源"),
                "doc_id": md.get("doc_id"),
                "category": md.get("category", ""),
                "snippet": hit.content[:200],
            }
        )
    return refs


async def school_info_stream(
    db: Session, session_id: int, question: str
) -> AsyncGenerator[tuple[str, str], None]:
    """学校信息问答流式生成器。结束时附带 refs 事件。"""
    history = build_context_messages(db, session_id)
    hits = rag_pipeline.search(question)
    if not hits:
        yield "token", NOT_FOUND_TEXT
        yield "refs", []
        yield "done", {"status": "ok"}
        return

    context = rag_pipeline.format_context(hits)
    system = templates.SCHOOL_SYSTEM_PROMPT + "\n\n" + templates.RAG_CONTEXT_TEMPLATE.format(context=context)
    messages = [SystemMessage(content=system)]
    # 上下文联合思考：按角色完整注入历史多轮对话
    messages.extend(history_to_lc_messages(history))
    messages.append(HumanMessage(content=f"问题：{question}"))

    try:
        llm = llm_factory.get_chat_model(task="school_info", stream=True)
        full = ""
        async for chunk in llm.astream(messages):
            piece = chunk.content or ""
            if piece:
                full += piece
                yield "token", piece
        refs = _parse_refs(full, hits)
        yield "refs", refs
        yield "done", {"status": "ok", "full": full}
    except Exception as exc:
        logger.error("学校信息问答失败: %s", exc)
        yield "error", {"message": f"模型调用失败：{exc}"}
