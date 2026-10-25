"""通用问答服务：意图分流（学校信息关键词 → RAG 增强）、开放问答、兜底、流式输出。

通用问答新增「分支推理」：收到问题后先让 LLM 给出 2~3 个思路方案（title/note/score），
选定最优后流式作答。事件序列：branches → chosen → token* → done。
"""
import json
import re
from typing import AsyncGenerator

from langchain_core.messages import HumanMessage, SystemMessage
from sqlalchemy.orm import Session

from app.prompts import templates
from app.services.llm_factory import llm_factory
from app.services.rag_pipeline import rag_pipeline
from app.services.session_manager import build_context_messages, history_to_lc_messages
from app.utils.logging_conf import get_logger

logger = get_logger("chat_service")

# 触发知识库增强的学校信息关键词（可扩展）
SCHOOL_KEYWORDS = [
    "招生", "报名", "入学", "作息", "放学", "上学", "校历", "放假", "假期",
    "转学", "证明", "教务处", "电话", "地址", "规章制度", "校规", "通知",
    "班级", "师资", "教师", "食堂", "午餐", "保险", "课后服务", "社团",
]

# 简易敏感词（演示用，生产可接审核服务）
SENSITIVE_WORDS = ["赌博", "色情", "毒品", "枪支", "暴力恐怖"]


def _check_sensitive(question: str) -> str | None:
    for word in SENSITIVE_WORDS:
        if word in question:
            return "该内容涉及敏感话题，我无法回答。如有需要请咨询家长或老师。"
    return None


def _need_school_rag(question: str) -> bool:
    return any(kw in question for kw in SCHOOL_KEYWORDS)


def _parse_branches(raw: str) -> list[dict]:
    """解析分支推理 LLM 输出，得到规范化思路列表（最多 3 条）。"""
    text = (raw or "").strip()
    if not text:
        return []
    # 去掉可能包裹的 ```json ... ``` 代码块标记
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    # 截取第一个 JSON 数组
    m = re.search(r"\[[\s\S]*\]", text)
    if m:
        text = m.group(0)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return []
    if not isinstance(data, list):
        return []

    branches: list[dict] = []
    for i, item in enumerate(data):
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        note = str(item.get("note", "")).strip()
        if not title:
            continue
        try:
            score = int(item.get("score", 0))
        except (TypeError, ValueError):
            score = 0
        score = max(0, min(100, score))
        branches.append({"id": f"a{i + 1}", "title": title, "note": note, "score": score})
        if len(branches) >= 3:
            break
    return branches


async def _generate_branches(messages: list) -> list[dict]:
    """调用 LLM 非流式生成 2~3 个思路方案。失败时返回空列表（退化为单路回答）。"""
    branch_messages = [SystemMessage(content=templates.BRANCHING_SYSTEM_PROMPT)] + messages
    try:
        llm = llm_factory.get_chat_model(task="general", stream=False)
        resp = await llm.ainvoke(branch_messages)
        return _parse_branches(resp.content or "")
    except Exception as exc:  # pragma: no cover - 由上层保证不致命
        logger.warning("分支推理生成失败，退化为单路回答: %s", exc)
        return []


async def chat_stream(
    db: Session, session_id: int, question: str
) -> AsyncGenerator[tuple[str, str], None]:
    """通用问答流式生成器。yield (event, data_json_str)；最终由路由层负责落库。"""
    blocked = _check_sensitive(question)
    if blocked:
        yield "token", blocked
        yield "done", {"status": "ok"}
        return

    history = build_context_messages(db, session_id)
    use_rag = _need_school_rag(question)
    context = ""
    if use_rag:
        hits = rag_pipeline.search(question)
        if hits:
            context = rag_pipeline.format_context(hits)

    system = templates.GENERAL_SYSTEM_PROMPT
    if context:
        system += "\n\n" + templates.RAG_CONTEXT_TEMPLATE.format(context=context)

    messages = [SystemMessage(content=system)]
    # 上下文联合思考：把历史多轮对话按角色完整注入，而非拍平成文本
    messages.extend(history_to_lc_messages(history))
    messages.append(HumanMessage(content=question))

    try:
        # 1) 分支推理：先给出 2~3 个思路方案并选定最优
        branches = await _generate_branches(messages)
        chosen_id: str | None = None
        if branches:
            chosen = max(branches, key=lambda b: b["score"])
            chosen_id = chosen["id"]
            yield "branches", {"branches": branches}
            yield "chosen", {"id": chosen_id}

        # 2) 按选定思路流式作答
        answer_messages = list(messages)
        if chosen_id:
            chosen = next(b for b in branches if b["id"] == chosen_id)
            answer_messages.append(
                HumanMessage(content=f"（已选定最优思路：{chosen['title']}）请按该思路作答。")
            )

        llm = llm_factory.get_chat_model(task="general", stream=True)
        full = ""
        async for chunk in llm.astream(answer_messages):
            piece = chunk.content or ""
            if piece:
                full += piece
                yield "token", piece
        yield "done", {"status": "ok", "full": full}
    except Exception as exc:
        logger.error("通用问答失败: %s", exc)
        yield "error", {"message": f"模型调用失败：{exc}"}
