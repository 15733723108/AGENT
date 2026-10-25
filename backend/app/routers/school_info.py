"""学校信息问答路由：RAG 知识库增强 + 引用来源 + SSE 流式。"""
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.entities import User
from app.routers.deps import get_current_user
from app.schemas.chat import ChatHistoryOut, ChatRequest, ChatMessageOut, SessionCreateRequest, SessionOut
from app.services.school_info_service import school_info_stream
from app.services.session_manager import append_message, create_session, delete_session, get_history, get_session, list_sessions
from app.utils.rate_limit import check_rate_limit
from app.utils.sse import sse_event

router = APIRouter()


def _session_out(s: object) -> SessionOut:
    return SessionOut(
        id=s.id,
        module=s.module,
        title=s.title,
        created_at=str(s.created_at) if s.created_at else None,
        updated_at=str(s.updated_at) if s.updated_at else None,
    )


def _session_title(question: str) -> str:
    """会话标题：取首问的简称（压缩空白、超长截断加省略号）。"""
    collapsed = " ".join(question.split())
    return collapsed if len(collapsed) <= 16 else collapsed[:16] + "…"


def _msg_out(m: object) -> ChatMessageOut:
    raw = m.refs
    refs = None
    if isinstance(raw, str) and raw.strip():
        try:
            refs = json.loads(raw)
        except json.JSONDecodeError:
            refs = None
    elif isinstance(raw, list):
        refs = raw
    return ChatMessageOut(
        id=m.id,
        role=m.role,
        content=m.content,
        refs=refs,
        created_at=str(m.created_at) if m.created_at else None,
    )


@router.post("/sessions", response_model=SessionOut, summary="创建学校信息问答会话")
def create(req: SessionCreateRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = create_session(db, user.id, module="school_info", title=req.title)
    return _session_out(s)


@router.get("/sessions", response_model=list[SessionOut], summary="学校信息问答会话列表")
def session_list(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return [_session_out(s) for s in list_sessions(db, user.id, module="school_info")]


@router.delete("/sessions/{session_id}", summary="删除会话")
def remove(session_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = get_session(db, session_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")
    delete_session(db, session_id)
    return {"status": "ok"}


@router.get("/sessions/{session_id}/history", response_model=ChatHistoryOut, summary="会话历史")
def history(session_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = get_session(db, session_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")
    msgs = get_history(db, session_id)
    return ChatHistoryOut(session=_session_out(s), messages=[_msg_out(m) for m in msgs])


@router.post("/chat", summary="学校信息问答（SSE 流式，含引用来源）")
async def chat(req: ChatRequest, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = get_session(db, req.session_id)
    if not s or s.user_id != user.id:
        raise HTTPException(status_code=404, detail="会话不存在")
    if not check_rate_limit(user.id, "school_info", limit=30, window=60):
        raise HTTPException(status_code=429, detail="请求过于频繁，请稍后再试")

    if (not s.title or s.title.startswith("新会话")) and len(req.question) > 2:
        s.title = _session_title(req.question)
        db.commit()

    assistant_full = ""
    refs = None

    async def gen():
        nonlocal assistant_full, refs
        try:
            async for event, data in school_info_stream(db, req.session_id, req.question):
                if event == "token":
                    assistant_full += data
                    yield sse_event("token", {"text": data})
                elif event == "refs":
                    refs = data
                    yield sse_event("refs", data)
                elif event == "done":
                    yield sse_event("done", data)
                elif event == "error":
                    yield sse_event("error", data)
        finally:
            append_message(db, req.session_id, "user", req.question)
            append_message(db, req.session_id, "assistant", assistant_full, refs=refs)

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})
