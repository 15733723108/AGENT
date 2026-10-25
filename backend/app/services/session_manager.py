"""会话管理：会话创建、多轮记忆窗口、消息落库。

记忆策略（对齐开发文档 3.1.3）：窗口最近 N 轮（默认 10 轮），
优先从 MySQL 读取历史；Redis 作为热缓存（chat:{session_id}）。
"""
import json
from typing import Optional

from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.config import settings
from app.models.entities import ChatMessage, ChatSession
from app.utils.rate_limit import get_redis


def create_session(db: Session, user_id: int, module: str, title: str = "") -> ChatSession:
    session = ChatSession(user_id=user_id, module=module, title=title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: Session, session_id: int) -> Optional[ChatSession]:
    return db.query(ChatSession).filter(ChatSession.id == session_id).first()


def list_sessions(db: Session, user_id: int, module: Optional[str] = None) -> list[ChatSession]:
    """按最近活跃倒序返回当前用户（可指定模块）的非空会话列表（排除无消息的占位会话）。"""
    q = db.query(ChatSession).filter(ChatSession.user_id == user_id)
    if module:
        q = q.filter(ChatSession.module == module)
    has_messages = db.query(ChatMessage.id).filter(ChatMessage.session_id == ChatSession.id).exists()
    q = q.filter(has_messages)
    return q.order_by(ChatSession.updated_at.desc(), ChatSession.id.desc()).all()


def delete_empty_sessions(db: Session, user_id: Optional[int] = None, module: Optional[str] = None) -> int:
    """删除没有任何消息的「占位」会话，返回删除数量。"""
    has_messages = db.query(ChatMessage.id).filter(ChatMessage.session_id == ChatSession.id).exists()
    q = db.query(ChatSession.id).filter(~has_messages)
    if user_id is not None:
        q = q.filter(ChatSession.user_id == user_id)
    if module:
        q = q.filter(ChatSession.module == module)
    ids = [row[0] for row in q.all()]
    if not ids:
        return 0
    deleted = db.query(ChatSession).filter(ChatSession.id.in_(ids)).delete(synchronize_session=False)
    db.commit()
    return deleted


def delete_session(db: Session, session_id: int) -> bool:
    """删除会话及其全部消息。返回是否实际删除。"""
    session = get_session(db, session_id)
    if not session:
        return False
    db.query(ChatMessage).filter(ChatMessage.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return True


def history_to_lc_messages(history: list[dict]) -> list:
    """把历史消息（role/content dict）转为 LangChain 消息对象，保留多轮对话结构。"""
    msgs = []
    for m in history:
        if m.get("role") == "assistant":
            msgs.append(AIMessage(content=m.get("content", "")))
        else:
            msgs.append(HumanMessage(content=m.get("content", "")))
    return msgs


def _load_recent_messages(db: Session, session_id: int, window: int):
    return (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.id.desc())
        .limit(window * 2)
        .all()[::-1]
    )


def build_context_messages(db: Session, session_id: int) -> list[dict]:
    """组装 LangChain 可用的历史消息列表（最近 N 轮）。"""
    messages = _load_recent_messages(db, session_id, settings.CHAT_MEMORY_WINDOW)
    return [{"role": m.role, "content": m.content} for m in messages]


def get_history(db: Session, session_id: int, window: Optional[int] = None) -> list[ChatMessage]:
    window = window or settings.CHAT_MEMORY_WINDOW * 2
    return _load_recent_messages(db, session_id, window)


def append_message(
    db: Session,
    session_id: int,
    role: str,
    content: str,
    refs: Optional[list] = None,
    token_count: int = 0,
    latency_ms: int = 0,
) -> ChatMessage:
    msg = ChatMessage(
        session_id=session_id,
        role=role,
        content=content,
        refs=json.dumps(refs, ensure_ascii=False) if refs else None,
        token_count=token_count,
        latency_ms=latency_ms,
    )
    db.add(msg)
    # 同步会话活跃时间，供「历史会话」列表按最近使用排序
    db.query(ChatSession).filter(ChatSession.id == session_id).update(
        {"updated_at": func.now()}, synchronize_session=False
    )
    db.commit()
    db.refresh(msg)
    # 更新会话热缓存（标记会话有活动）
    redis = get_redis()
    redis.set(f"chat:{session_id}", "1", ex=7 * 86400)
    return msg
